"""Offline audiovisual continuity contract validation for rendered-shot manifests.

This validates declared frame/voice references against replay-verified persona,
body, and object state. It does NOT inspect pixels or acoustic voice similarity.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from .embodiment import project_embodiment

MAX_MANIFEST_BYTES = 2_000_000
MAX_SHOTS = 200
MAX_CAST_PER_SHOT = 32
SHA256_LENGTH = 64


def read_manifest(path: Path) -> dict:
    if path.stat().st_size > MAX_MANIFEST_BYTES:
        raise ValueError("audiovisual manifest exceeds 2 MB")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise ValueError("audiovisual manifest must be UTF-8 JSON") from exc
    validate_manifest(payload)
    return payload


def _string(value, label):
    if not isinstance(value, str) or not value.strip() or len(value) > 256:
        raise ValueError(f"invalid {label}")
    return value


def validate_manifest(manifest: object):
    if not isinstance(manifest, dict) or manifest.get("version") != 1:
        raise ValueError("audiovisual manifest version must be 1")
    _string(manifest.get("world_id"), "world_id")
    _string(manifest.get("as_of"), "as_of")
    shots = manifest.get("shots")
    if not isinstance(shots, list) or not 1 <= len(shots) <= MAX_SHOTS:
        raise ValueError("shots must contain 1 to 200 entries")
    seen = set()
    last_index = -1
    for shot in shots:
        if not isinstance(shot, dict):
            raise ValueError("shot must be an object")
        sid = _string(shot.get("shot_id"), "shot_id")
        if sid in seen:
            raise ValueError("duplicate shot_id")
        seen.add(sid)
        position = shot.get("index")
        if type(position) is not int or position <= last_index:
            raise ValueError("shot indices must be strictly increasing")
        last_index = position
        cast = shot.get("cast")
        if not isinstance(cast, list) or len(cast) > MAX_CAST_PER_SHOT:
            raise ValueError("cast must be an array of up to 32 entries")
        cast_seen = set()
        for observed in cast:
            if not isinstance(observed, dict):
                raise ValueError("invalid cast entry")
            pid = _string(observed.get("identity_id"), "identity_id")
            if pid in cast_seen:
                raise ValueError("duplicate cast identity in shot")
            cast_seen.add(pid)
            for name in ("body_id", "body_visual_anchor", "body_vocal_anchor",
                         "identity_voice_anchor", "clothing"):
                _string(observed.get(name), name)
            items = observed.get("visible_equipment")
            if not isinstance(items, list) or len(items) != len(set(items)):
                raise ValueError("visible_equipment must be unique array")
            for item in items:
                _string(item, "equipment ID")
            if not isinstance(observed.get("voice_active"), bool):
                raise ValueError("voice_active must be boolean")
            image = observed.get("rendered_image_sha256")
            if image is not None and (not isinstance(image, str) or len(image) != SHA256_LENGTH
                                      or any(ch not in "0123456789abcdef" for ch in image)):
                raise ValueError("invalid rendered image sha256")
            audio = observed.get("rendered_audio_sha256")
            if audio is not None and (not isinstance(audio, str) or len(audio) != SHA256_LENGTH
                                      or any(ch not in "0123456789abcdef" for ch in audio)):
                raise ValueError("invalid rendered audio sha256")
    return manifest


def validate_av_continuity(manifest: dict, world_snapshot: dict, identity_registry, binding_registry):
    """Deterministic metadata contract audit. Unobserved visual content is unknown."""
    from .adapter import validate_world_snapshot
    from .identity_adapter import project_identities

    validate_manifest(manifest)
    validate_world_snapshot(world_snapshot)
    identities = project_identities(world_snapshot, identity_registry)
    bound = project_embodiment(identity_registry, binding_registry)
    if manifest["world_id"] != world_snapshot["world_id"]:
        raise ValueError("AV manifest world_id mismatch")
    if manifest["as_of"] != world_snapshot["time"] or bound["as_of"] != world_snapshot["time"]:
        raise ValueError("AV manifest timestamp differs from canonical ledgers")
    verified_cast = set(identities["characters"])
    findings = []
    checked = 0
    hash_evidence_count = 0
    for shot in manifest["shots"]:
        for actual in shot["cast"]:
            checked += 1
            sid, pid = shot["shot_id"], actual["identity_id"]
            if pid not in verified_cast:
                findings.append({"shot_id": sid, "identity_id": pid,
                                 "field": "identity_id", "expected": "observed world participant",
                                 "actual": pid, "severity": "error"})
                continue
            expected = bound["characters"][pid]
            fields = {
                "body_id": expected["body_id"],
                "body_visual_anchor": expected["body"]["visual_anchor"],
                "body_vocal_anchor": expected["body"]["vocal_anchor"],
                "identity_voice_anchor": expected["identity_voice_anchor"],
                "clothing": expected["body"]["clothing"],
            }
            for field, desired in fields.items():
                if actual[field] != desired:
                    findings.append({"shot_id": sid, "identity_id": pid,
                                     "field": field, "expected": desired,
                                     "actual": actual[field], "severity": "error"})
            required_items = set(expected["worn"])
            recorded_items = set(actual["visible_equipment"])
            for item in sorted(required_items ^ recorded_items):
                findings.append({"shot_id": sid, "identity_id": pid,
                                 "field": "visible_equipment", "expected": sorted(required_items),
                                 "actual": sorted(recorded_items), "severity": "error",
                                 "item_id": item})
            for field in ("rendered_image_sha256", "rendered_audio_sha256"):
                if actual.get(field):
                    hash_evidence_count += 1
            if actual["voice_active"] and not actual.get("rendered_audio_sha256"):
                findings.append({"shot_id": sid, "identity_id": pid,
                                 "field": "rendered_audio_sha256", "severity": "unknown",
                                 "detail": "speaking character has no audio content hash"})
    errors = sum(x["severity"] == "error" for x in findings)
    return {
        "version": 1, "world_id": manifest["world_id"], "as_of": manifest["as_of"],
        "shots": len(manifest["shots"]), "cast_observations": checked,
        "status": "metadata_mismatch" if errors else "metadata_consistent",
        "error_count": errors,
        "hash_evidence_count": hash_evidence_count,
        "findings": findings,
        "scope": "declared shot metadata and optional content digests only; no image/audio perceptual verification",
    }


def check_media_hash(path: Path, expected_sha256: str) -> bool:
    """Optional exact content integrity check, not visual or voice comparison."""
    if not isinstance(expected_sha256, str) or len(expected_sha256) != 64 or any(
        ch not in "0123456789abcdef" for ch in expected_sha256
    ):
        raise ValueError("invalid SHA-256")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            block = stream.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest() == expected_sha256
