"""Offline media evidence inspection with per-shot, time-specific world states.

Checks actual local image pixels (Pillow) and PCM WAV sample differences; scores
are generic signal differences, NOT face identity or voice identity recognition.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import wave

from .adapter import load_world_snapshot
from .identity_adapter import load_identity_snapshot
from .embodiment import load_binding_snapshot
from .av_continuity import read_manifest, validate_av_continuity

MAX_BYTES = 2_000_000
MAX_SHOTS = 200
MAX_MEDIA_BYTES = 80_000_000
MAX_AUDIO_FRAMES = 4_000_000
MAX_IMAGE_PIXELS = 20_000_000


def _text(value, name):
    if not isinstance(value, str) or not value.strip() or len(value) > 512:
        raise ValueError(f"invalid {name}")
    return value


def _local(root: Path, value: str) -> Path:
    name = _text(value, "local file path")
    path = Path(name)
    if path.is_absolute():
        raise ValueError("absolute media paths are prohibited")
    base = root.resolve(strict=True)
    selected = (base / path).resolve(strict=True)
    if not selected.is_relative_to(base) or not selected.is_file():
        raise ValueError("path escapes approved media root or is not a file")
    if selected.stat().st_size > MAX_MEDIA_BYTES:
        raise ValueError("media file exceeds size limit")
    return selected


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(data)
    return digest.hexdigest()


def _hash(path: Path, expected: str | None) -> dict:
    actual = _sha256(path)
    if expected is not None and (
        not isinstance(expected, str) or len(expected) != 64
        or any(ch not in "0123456789abcdef" for ch in expected)
    ):
        raise ValueError("invalid expected SHA-256 digest")
    return {"sha256": actual, "expected_sha256": expected,
            "integrity": "match" if expected == actual else (
                "mismatch" if expected else "unverified")}


def _image_distance(reference: Path, rendered: Path) -> dict:
    try:
        from PIL import Image, ImageChops, ImageStat, UnidentifiedImageError
    except ImportError as exc:
        raise ValueError("Pillow is required for image evidence analysis") from exc
    try:
        with Image.open(reference) as im:
            im.load()
            if im.width * im.height > MAX_IMAGE_PIXELS:
                raise ValueError("reference image exceeds pixel limit")
            a = im.convert("RGB")
        with Image.open(rendered) as im:
            im.load()
            if im.width * im.height > MAX_IMAGE_PIXELS:
                raise ValueError("rendered image exceeds pixel limit")
            b = im.convert("RGB")
    except (OSError, UnidentifiedImageError) as exc:
        raise ValueError("unsupported or damaged image") from exc
    if a.size != b.size:
        return {"status": "incomparable", "reason": "image dimensions differ",
                "reference_size": list(a.size), "rendered_size": list(b.size)}
    if not a.width or not a.height:
        raise ValueError("empty image")
    delta = ImageChops.difference(a, b)
    mean = ImageStat.Stat(delta).mean
    mae = sum(mean) / (3 * 255)
    return {"status": "compared", "normalized_mae": round(mae, 6),
            "reference_size": list(a.size), "rendered_size": list(b.size),
            "method": "RGB pixel mean absolute error; alignment required"}


def _pcm(path: Path):
    if path.suffix.lower() != ".wav":
        raise ValueError("audio evidence must be PCM .wav")
    try:
        with wave.open(str(path), "rb") as reader:
            if reader.getcomptype() != "NONE":
                raise ValueError("compressed WAV not supported")
            channels, width, rate, frames = (
                reader.getnchannels(), reader.getsampwidth(),
                reader.getframerate(), reader.getnframes()
            )
            if channels not in (1, 2) or width != 2 or rate <= 0 or frames > MAX_AUDIO_FRAMES:
                raise ValueError("audio must be mono/stereo 16-bit PCM WAV within limits")
            blob = reader.readframes(frames)
    except (wave.Error, EOFError, OSError) as exc:
        raise ValueError("invalid WAV audio") from exc
    from array import array
    import sys
    samples = array("h")
    samples.frombytes(blob)
    if sys.byteorder != "little":
        samples.byteswap()
    return (channels, rate, frames), samples


def _audio_distance(reference: Path, rendered: Path) -> dict:
    m1, a = _pcm(reference)
    m2, b = _pcm(rendered)
    if m1 != m2:
        return {"status": "incomparable", "reason": "audio format or duration differs",
                "reference_format": list(m1), "rendered_format": list(m2)}
    if not a:
        return {"status": "incomparable", "reason": "empty audio"}
    # Sample-aligned PCM difference. High scores may reflect timing or pitch,
    # not a different speaker; never interpret as speaker identity.
    total = sum(abs(x - y) for x, y in zip(a, b))
    difference = total / (len(a) * 65535)
    return {"status": "compared", "normalized_sample_mae": round(difference, 6),
            "channels": m1[0], "sample_rate": m1[1], "frames": m1[2],
            "method": "aligned PCM sample mean absolute error; not speaker recognition"}


def load_evidence_plan(path: Path) -> dict:
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("evidence plan exceeds 2 MB")
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("evidence plan must be valid UTF-8 JSON") from exc
    if not isinstance(plan, dict) or plan.get("version") != 1:
        raise ValueError("unsupported evidence plan version")
    if not isinstance(plan.get("shots"), list) or not 1 <= len(plan["shots"]) <= MAX_SHOTS:
        raise ValueError("plan must contain 1 to 200 shots")
    if set(plan) - {"version", "shots", "image_threshold", "audio_threshold"}:
        raise ValueError("unknown evidence plan keys")
    for key in ("image_threshold", "audio_threshold"):
        threshold = plan.get(key, 0.1)
        if type(threshold) not in (float, int) or not math.isfinite(threshold) or not 0 <= threshold <= 1:
            raise ValueError("threshold must be in [0, 1]")
    previous, ids = None, set()
    for shot in plan["shots"]:
        if not isinstance(shot, dict) or set(shot) - {
            "shot_id", "at", "av_manifest", "world_snapshot", "identity_snapshot",
            "asset_bindings", "media"
        }:
            raise ValueError("invalid shot entry")
        name = _text(shot.get("shot_id"), "shot_id")
        if name in ids:
            raise ValueError("duplicate shot ID")
        ids.add(name)
        from .identity import utc
        when = utc(_text(shot.get("at"), "shot timestamp"))
        if previous is not None and when < previous:
            raise ValueError("shot timestamps must not go backwards")
        previous = when
        for name in ("av_manifest", "world_snapshot", "identity_snapshot", "asset_bindings"):
            _text(shot.get(name), name)
        media = shot.get("media")
        if not isinstance(media, list) or not media:
            raise ValueError("shot must declare media evidence")
        seen = set()
        for entry in media:
            if not isinstance(entry, dict) or set(entry) - {
                "identity_id", "kind", "reference", "rendered", "rendered_sha256"
            }:
                raise ValueError("invalid media entry")
            pid = _text(entry.get("identity_id"), "identity_id")
            kind = entry.get("kind")
            if kind not in ("image", "audio") or (pid, kind) in seen:
                raise ValueError("duplicate or invalid identity media kind")
            seen.add((pid, kind))
            _text(entry.get("reference"), "reference")
            _text(entry.get("rendered"), "rendered")
    return plan


def analyze_evidence(plan: dict, root: Path) -> dict:
    """Report per-shot source continuity plus actual file-level evidence."""
    findings, shot_reports = [], []
    errors, unknown = 0, 0
    for shot in plan["shots"]:
        local = lambda name: _local(root, shot[name])
        world = load_world_snapshot(local("world_snapshot"))
        identity = load_identity_snapshot(local("identity_snapshot"))
        binding = load_binding_snapshot(local("asset_bindings"))
        manifest = read_manifest(local("av_manifest"))
        if len(manifest["shots"]) != 1 or manifest["shots"][0]["shot_id"] != shot["shot_id"]:
            raise ValueError("each time-scoped manifest must contain exactly its corresponding shot")
        if shot["at"] != world["time"] or shot["at"] != manifest["as_of"]:
            raise ValueError("shot timestamp does not match canonical projection")
        metadata = validate_av_continuity(manifest, world, identity, binding)
        shot_errors = metadata["error_count"]
        errors += shot_errors
        unknown += sum(f["severity"] == "unknown" for f in metadata["findings"])
        observations = {entry["identity_id"]: entry for entry in manifest["shots"][0]["cast"]}
        media_checks = []
        for entry in shot["media"]:
            pid = entry["identity_id"]
            if pid not in observations:
                raise ValueError("media character absent from shot cast")
            kind = entry["kind"]
            reference = _local(root, entry["reference"])
            rendered = _local(root, entry["rendered"])
            manifest_digest = observations[pid].get(
                "rendered_image_sha256" if kind == "image" else "rendered_audio_sha256"
            )
            provided_digest = entry.get("rendered_sha256")
            if manifest_digest and provided_digest and manifest_digest != provided_digest:
                raise ValueError("plan and manifest media hashes disagree")
            digest = _hash(rendered, provided_digest or manifest_digest)
            if digest["integrity"] == "mismatch":
                errors += 1
                findings.append({"shot_id": shot["shot_id"], "identity_id": pid,
                                 "field": "media_integrity", "severity": "error",
                                 "kind": kind})
            if kind == "image":
                comparison = _image_distance(reference, rendered)
                threshold = plan.get("image_threshold", 0.1)
                metric = "normalized_mae"
            else:
                comparison = _audio_distance(reference, rendered)
                threshold = plan.get("audio_threshold", 0.1)
                metric = "normalized_sample_mae"
                if not observations[pid]["voice_active"]:
                    unknown += 1
                    findings.append({"shot_id": shot["shot_id"], "identity_id": pid,
                                     "field": "audio_evidence", "severity": "unknown",
                                     "detail": "voice is declared inactive"})
            if comparison["status"] != "compared":
                unknown += 1
                findings.append({"shot_id": shot["shot_id"], "identity_id": pid,
                                 "field": kind + "_alignment", "severity": "unknown",
                                 "detail": comparison["reason"]})
            elif comparison[metric] > threshold:
                errors += 1
                findings.append({"shot_id": shot["shot_id"], "identity_id": pid,
                                 "field": kind + "_difference", "severity": "error",
                                 "score": comparison[metric], "threshold": threshold,
                                 "detail": "generic signal difference; manual continuity review required"})
            media_checks.append({"identity_id": pid, "kind": kind, "hash": digest,
                                 "comparison": comparison})
        available = {(item["identity_id"], item["kind"]) for item in shot["media"]}
        for person in manifest["shots"][0]["cast"]:
            if person["voice_active"] and (person["identity_id"], "audio") not in available:
                unknown += 1
                findings.append({"shot_id": shot["shot_id"],
                                 "identity_id": person["identity_id"],
                                 "field": "missing_audio_evidence", "severity": "unknown"})
        shot_reports.append({"shot_id": shot["shot_id"], "at": shot["at"],
                             "metadata": metadata, "media": media_checks})
    return {
        "version": 1,
        "status": "review_required" if errors else ("partial_evidence" if unknown else "checks_passed"),
        "error_count": errors, "unknown_count": unknown,
        "shots": shot_reports, "findings": findings,
        "scope": "actual local image/PCM differences, hash integrity, and per-shot canonical metadata; no character/voice identity recognition",
    }
