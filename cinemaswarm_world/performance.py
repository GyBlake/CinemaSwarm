"""Fail-closed human-reviewed audio and mouth-performance evidence.

Audio hashes are verified from local source recordings. Lip offsets and
perceived voice/character fit are reviewer-attested, NOT automatically inferred
from sound samples or model internals.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
from .collaboration import validate_package, text

MAX_AUDIO = 200_000_000
MAX_OFFSET_MS = 80

def _media(root, name):
    path = Path(text(name, "audio path"))
    if path.is_absolute() or path.suffix.lower() not in (".wav", ".flac"):
        raise ValueError("audio must be relative WAV/FLAC")
    base = Path(root).resolve(strict=True)
    target = (base / path).resolve(strict=True)
    if not target.is_relative_to(base) or not target.is_file() or target.stat().st_size > MAX_AUDIO:
        raise ValueError("audio escapes approved root or unavailable")
    return target

def _sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def audit_performance(package, takes, root):
    validate_package(package)
    if not isinstance(takes, dict) or set(takes) != {"version", "episode_id", "takes"} or takes["version"] != 1 or takes["episode_id"] != package["episode_id"]:
        raise ValueError("invalid performance evidence manifest")
    entries = takes["takes"]
    if not isinstance(entries, list) or len(entries) > 600:
        raise ValueError("invalid takes list")
    by_id = {line["id"]: line for line in package["dialogue"]}
    seen, failures, unknowns, details = set(), [], [], []
    for take in entries:
        if not isinstance(take, dict) or set(take) != {"dialogue_id", "speaker_id", "voice_id",
                                                      "audio_source", "audio_sha256",
                                                      "voice_match_approved", "lip_sync_approved",
                                                      "sync_offset_ms", "reviewer", "evidence"}:
            raise ValueError("invalid take schema")
        lid = text(take["dialogue_id"], "take dialogue id")
        if lid in seen or lid not in by_id:
            raise ValueError("duplicate or unknown dialogue take")
        seen.add(lid)
        line = by_id[lid]
        failed = []
        if take["speaker_id"] != line["speaker_id"] or take["voice_id"] != line["voice_id"]:
            failed.append("speaker_voice_identity_mismatch")
        if take["voice_match_approved"] is not True:
            failed.append("voice_identity_not_approved")
        if line["channel"] == "onscreen":
            if take["lip_sync_approved"] is not True:
                failed.append("lip_sync_not_approved")
            offset = take["sync_offset_ms"]
            if type(offset) not in (float, int) or abs(offset) > MAX_OFFSET_MS:
                failed.append("lip_sync_offset_exceeds_limit_or_unmeasured")
        elif take["lip_sync_approved"] is True:
            failed.append("nonvisual_voice_must_not_claim_mouth_sync")
        text(take["reviewer"], "performance reviewer")
        text(take["evidence"], "performance evidence reference")
        path = _media(root, take["audio_source"])
        if _sha(path) != take["audio_sha256"]:
            failed.append("audio_integrity_mismatch")
        failures.extend(f"{lid}:{f}" for f in failed)
        details.append({"dialogue_id": lid, "status": "blocked" if failed else "reviewed",
                        "failed_checks": failed, "reviewer": take["reviewer"],
                        "evidence": take["evidence"], "audio_sha256": _sha(path),
                        "sync_offset_ms": take["sync_offset_ms"]})
    unknowns = [f"missing_take:{lid}" for lid in by_id if lid not in seen]
    status = "blocked" if failures else ("incomplete" if unknowns else "checks_passed")
    return {"version": 1, "episode_id": package["episode_id"], "status": status,
            "error_count": len(failures), "unknown_count": len(unknowns),
            "failures": failures, "unknowns": unknowns, "takes": details,
            "measurement_scope": "SHA-256 file measurement + human reviewer attestations; no automatic phoneme alignment"}
