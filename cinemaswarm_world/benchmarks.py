"""Evidence-first season delivery qualification for CinemaSwarm.

Profiles are studio policies informed by published references, NOT claims of
certification from YouTube, Netflix, EBU, C2PA or any festival. Fail closed.
"""
from __future__ import annotations

import hashlib
import json
import math
import subprocess
import re
from pathlib import Path

SCHEMA_VERSION = 1
MAX_MANIFEST_BYTES = 2_000_000
MAX_MEDIA_BYTES = 4_000_000_000
MAX_EPISODES = 200
MANDATORY_REVIEWS = ("narrative", "performance", "visual_identity", "voice_identity", "cinematography")
WEIGHTS = {"narrative": 25, "performance": 20, "visual_identity": 25,
           "voice_identity": 20, "cinematography": 10}
PROFILES = {
    "vertical-premium-v1": {
        "label": "CinemaSwarm premium vertical master, NOT platform certification",
        "min_width": 1080, "min_height": 1920, "aspect_ratio": 9 / 16,
        "min_duration": 60, "max_duration": 180,
        "fps_min": 23, "fps_max": 61,
        "audio_sample_rate": 48000,
        "allowed_video_codecs": ("h264", "hevc", "av1"),
        "allowed_audio_codecs": ("aac", "opus", "flac", "pcm_s24le", "pcm_s16le"),
        "min_human_score": 95,
        "loudness_target": -16.0, "loudness_tolerance": 2.0,
        "peak_limit": -1.0,
        "captions_required": True,
        "provenance_required": True,
    },
    "cinematic-horizontal-v1": {
        "label": "CinemaSwarm high-resolution 16:9 master, NOT OTT/DCP/IMF approval",
        "min_width": 3840, "min_height": 2160, "aspect_ratio": 16 / 9,
        "min_duration": 60, "max_duration": 7200,
        "fps_min": 23, "fps_max": 61,
        "audio_sample_rate": 48000,
        "allowed_video_codecs": ("prores", "hevc", "h264", "av1"),
        "allowed_audio_codecs": ("aac", "flac", "pcm_s24le", "pcm_s16le"),
        "min_human_score": 95,
        "loudness_target": -23.0, "loudness_tolerance": 1.0,
        "peak_limit": -1.0,
        "captions_required": True,
        "provenance_required": True,
    },
}


def _bounded_text(value, name):
    if not isinstance(value, str) or not value.strip() or len(value) > 256:
        raise ValueError(f"invalid {name}")
    return value


def _file(root: Path, name: str) -> Path:
    path = Path(_bounded_text(name, "asset path"))
    if path.is_absolute():
        raise ValueError("absolute paths forbidden")
    base = root.resolve(strict=True)
    candidate = (base / path).resolve(strict=True)
    if not candidate.is_relative_to(base) or not candidate.is_file():
        raise ValueError("asset escapes approved root or is not a file")
    if candidate.stat().st_size > MAX_MEDIA_BYTES:
        raise ValueError("asset exceeds size cap")
    return candidate


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _frame_rate(text: str) -> float:
    try:
        numerator, denominator = str(text).split("/")
        rate = float(numerator) / float(denominator)
        if not math.isfinite(rate):
            raise ValueError()
        return rate
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError("invalid reported frame rate") from exc


def probe_media(path: Path) -> dict:
    """Use real local ffprobe output; never trust self-reported stream metadata."""
    try:
        process = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration:stream=index,codec_type,codec_name,width,height,"
             "avg_frame_rate,sample_rate", "-of", "json", str(path)],
            capture_output=True, text=True, timeout=30, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError("ffprobe unavailable or timed out") from exc
    if process.returncode != 0:
        raise ValueError("ffprobe failed to inspect media")
    try:
        result = json.loads(process.stdout)
        duration = float(result["format"]["duration"])
        tracks = result["streams"]
    except (KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid ffprobe stream metadata") from exc
    if not math.isfinite(duration) or duration <= 0 or not isinstance(tracks, list):
        raise ValueError("invalid media duration or tracks")
    video = [t for t in tracks if t.get("codec_type") == "video"]
    audio = [t for t in tracks if t.get("codec_type") == "audio"]
    if not video or not audio:
        raise ValueError("expected both video and audio streams")
    primary_video, primary_audio = video[0], audio[0]
    try:
        return {
            "duration_seconds": duration,
            "width": int(primary_video["width"]), "height": int(primary_video["height"]),
            "fps": _frame_rate(primary_video["avg_frame_rate"]),
            "video_codec": primary_video["codec_name"],
            "audio_codec": primary_audio["codec_name"],
            "audio_sample_rate": int(primary_audio["sample_rate"]),
            "video_tracks": len(video), "audio_tracks": len(audio),
            "method": "local ffprobe inspection",
        }
    except (KeyError, ValueError, TypeError) as exc:
        raise ValueError("incomplete decoded media metadata") from exc


def probe_loudness(path: Path) -> dict:
    """Measure real audio via ffmpeg ebur128; report LUFS and true peak.

    An internal policy target is used. This is NOT EBU broadcaster or
    streaming-distributor certification.
    """
    try:
        process = subprocess.run(
            ["ffmpeg", "-hide_banner", "-nostats", "-v", "info", "-i", str(path),
             "-filter_complex", "ebur128=peak=true", "-f", "null", "-"],
            capture_output=True, text=True, timeout=180, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError("ffmpeg EBU loudness probe unavailable") from exc
    if process.returncode != 0:
        raise ValueError("ffmpeg EBU loudness analysis failed")
    summary = process.stderr.rsplit("Summary:", 1)
    if len(summary) != 2:
        raise ValueError("EBU loudness summary unavailable")
    tail = summary[1]
    integrated = re.search(r"Integrated loudness:.*?\bI:\s*(-?[0-9]+(?:\.[0-9]+)?)\s*LUFS", tail, re.S)
    true_peak = re.search(r"True peak:.*?\bPeak:\s*(-?[0-9]+(?:\.[0-9]+)?)\s*dBFS", tail, re.S)
    if not integrated or not true_peak:
        raise ValueError("EBU loudness / true peak not measured")
    loudness, peak = float(integrated.group(1)), float(true_peak.group(1))
    if not math.isfinite(loudness) or not math.isfinite(peak):
        raise ValueError("invalid loudness measurement")
    return {"integrated_lufs": loudness, "true_peak_dbfs": peak,
            "method": "local ffmpeg ebur128 integrated and true-peak"}

def load_season_manifest(path: Path) -> dict:
    if path.stat().st_size > MAX_MANIFEST_BYTES:
        raise ValueError("season manifest exceeds 2 MB")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("season manifest must be UTF-8 JSON") from exc
    validate_season_manifest(data)
    return data


def validate_season_manifest(doc: object) -> dict:
    if not isinstance(doc, dict) or doc.get("version") != SCHEMA_VERSION:
        raise ValueError("season manifest version must be 1")
    _bounded_text(doc.get("season_id"), "season_id")
    if doc.get("profile") not in PROFILES:
        raise ValueError("unknown benchmark profile")
    expected = doc.get("planned_episodes")
    if type(expected) is not int or not 1 <= expected <= MAX_EPISODES:
        raise ValueError("planned_episodes must be between 1 and 200")
    episodes = doc.get("episodes")
    if not isinstance(episodes, list) or len(episodes) > expected:
        raise ValueError("invalid episode list")
    numbers = set()
    for ep in episodes:
        if not isinstance(ep, dict):
            raise ValueError("episode must be an object")
        number = ep.get("number")
        if type(number) is not int or not 1 <= number <= expected or number in numbers:
            raise ValueError("duplicate or invalid episode number")
        numbers.add(number)
        for field in ("master", "master_sha256", "captions", "captions_sha256",
                      "continuity_report", "provenance_record", "collaboration_package",
                      "collaboration_ack", "performance_report"):
            _bounded_text(ep.get(field), field)
        for field in ("master_sha256", "captions_sha256"):
            digest = ep[field]
            if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise ValueError("asset SHA-256 invalid")
        reviews = ep.get("reviews")
        if not isinstance(reviews, dict):
            raise ValueError("reviews must be an object")
        for dimension, item in reviews.items():
            if dimension not in MANDATORY_REVIEWS or not isinstance(item, dict):
                raise ValueError("unrecognized artistic review dimension")
            score = item.get("score")
            if type(score) not in (int, float) or not math.isfinite(score) or not 0 <= score <= 100:
                raise ValueError("review score must be between 0 and 100")
            _bounded_text(item.get("reviewer"), "reviewer")
            _bounded_text(item.get("evidence"), "review evidence")
            if item.get("approved") is not True:
                raise ValueError("reviews must have explicit approved=true")
    return doc


def _read_json_file(path: Path):
    if path.stat().st_size > MAX_MANIFEST_BYTES:
        raise ValueError("JSON evidence exceeds 2 MB")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid JSON evidence") from exc


def _episode(ep: dict, root: Path, profile: dict, season_id: str) -> dict:
    failures, unknowns, evidence = [], [], {}
    def fail(code):
        failures.append(code)
    def unknown(code):
        unknowns.append(code)
    try:
        master = _file(root, ep["master"])
        digest = _digest(master)
        evidence["master_sha256"] = digest
        if digest != ep["master_sha256"]:
            fail("master_hash_mismatch")
        info = probe_media(master)
        evidence["measured_media"] = info
        if info["width"] < profile["min_width"] or info["height"] < profile["min_height"]:
            fail("resolution_below_profile")
        if abs(info["width"] / info["height"] - profile["aspect_ratio"]) > 0.005:
            fail("aspect_ratio_mismatch")
        if not profile["min_duration"] <= info["duration_seconds"] <= profile["max_duration"]:
            fail("duration_outside_profile")
        if not profile["fps_min"] <= info["fps"] <= profile["fps_max"]:
            fail("frame_rate_outside_profile")
        if info["audio_sample_rate"] != profile["audio_sample_rate"]:
            fail("audio_sample_rate_mismatch")
        if info["video_codec"] not in profile["allowed_video_codecs"]:
            fail("video_codec_not_allowed")
        if info["audio_codec"] not in profile["allowed_audio_codecs"]:
            fail("audio_codec_not_allowed")
    except (OSError, ValueError) as exc:
        unknown("media_probe_or_file_unavailable")
        evidence["media_probe_error"] = str(exc)
    try:
        subtitle = _file(root, ep["captions"])
        if _digest(subtitle) != ep["captions_sha256"]:
            fail("captions_hash_mismatch")
        if subtitle.suffix.lower() not in (".srt", ".vtt"):
            fail("unsupported_caption_type")
        if not subtitle.read_text(encoding="utf-8").strip():
            fail("empty_captions")
    except (OSError, ValueError, UnicodeError):
        unknown("caption_file_unavailable")
    try:
        qc = _read_json_file(_file(root, ep["continuity_report"]))
        evidence["continuity_status"] = qc.get("status")
        if qc.get("status") != "checks_passed" or qc.get("error_count") != 0 or qc.get("unknown_count") != 0:
            fail("continuity_not_verified")
    except (OSError, ValueError, TypeError):
        unknown("continuity_report_unavailable")
    try:
        provenance = _read_json_file(_file(root, ep["provenance_record"]))
        if provenance.get("season_id") != season_id or provenance.get("episode_number") != ep["number"]:
            fail("provenance_identity_mismatch")
        if provenance.get("approved") is not True or not provenance.get("assets_licensed") is True:
            fail("provenance_approval_missing")
        evidence["provenance_type"] = provenance.get("type", "internal attestation")
        if provenance.get("c2pa_validated") is True:
            # Never claim C2PA conformance without an actual independent validator receipt.
            if not provenance.get("c2pa_validation_receipt"):
                unknown("c2pa_receipt_missing")
    except (OSError, ValueError, TypeError):
        unknown("provenance_record_unavailable")
    try:
        from .collaboration import load_json, validate_package, validate_acknowledgment, digest
        package = load_json(_file(root, ep["collaboration_package"]))
        validate_package(package)
        ack = load_json(_file(root, ep["collaboration_ack"]))
        validate_acknowledgment(package, ack)
        receipt = load_json(_file(root, ep["performance_report"]))
        if (receipt.get("package_sha256") != digest(package)
            or receipt.get("episode_id") != package["episode_id"]
            or receipt.get("status") != "checks_passed"
            or receipt.get("error_count") != 0
            or receipt.get("unknown_count") != 0):
            fail("performance_or_hydration_gate_failed")
        evidence["hydration_package_sha256"] = digest(package)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        unknown("hydration_performance_evidence_missing_or_unverified")
    reviews = ep["reviews"]
    missing = [key for key in MANDATORY_REVIEWS if key not in reviews]
    if missing:
        unknown("missing_human_reviews:" + ",".join(missing))
    score = None
    if not missing:
        score = round(sum(reviews[k]["score"] * WEIGHTS[k] for k in WEIGHTS) / 100, 2)
        evidence["weighted_artistic_score"] = score
        if score < profile["min_human_score"]:
            fail("artistic_score_below_studio_target")
        if any(reviews[k]["score"] < 85 for k in MANDATORY_REVIEWS):
            fail("critical_artistic_dimension_below_floor")
    try:
        measurement = probe_loudness(_file(root, ep["master"]))
        evidence["measured_loudness"] = measurement
        if abs(measurement["integrated_lufs"] - profile["loudness_target"]) > profile["loudness_tolerance"]:
            fail("integrated_loudness_outside_studio_target")
        if measurement["true_peak_dbfs"] > profile["peak_limit"]:
            fail("true_peak_above_studio_limit")
    except (OSError, ValueError) as exc:
        evidence["loudness_probe_error"] = str(exc)
        unknown("loudness_unmeasured")
    caption_review = ep.get("caption_review")
    if not isinstance(caption_review, dict):
        unknown("caption_accessibility_unreviewed")
    elif caption_review.get("approved") is not True:
        fail("captions_not_approved")
    rights_review = ep.get("rights_review")
    if not isinstance(rights_review, dict):
        unknown("rights_review_missing")
    elif rights_review.get("approved") is not True:
        fail("rights_review_not_approved")
    return {"number": ep["number"], "status": "blocked" if failures else ("incomplete" if unknowns else "qualified"),
            "failures": sorted(set(failures)), "unknowns": sorted(set(unknowns)),
            "artistic_score": score, "evidence": evidence}


def audit_season(doc: dict, root: Path) -> dict:
    validate_season_manifest(doc)
    profile = PROFILES[doc["profile"]]
    results = [_episode(ep, root, profile, doc["season_id"]) for ep in sorted(doc["episodes"], key=lambda x: x["number"])]
    present = {item["number"] for item in results}
    missing = [n for n in range(1, doc["planned_episodes"] + 1) if n not in present]
    statuses = [x["status"] for x in results]
    status = "blocked" if "blocked" in statuses else (
        "incomplete" if missing or "incomplete" in statuses else "qualified"
    )
    return {
        "version": 1, "season_id": doc["season_id"], "profile": doc["profile"],
        "profile_label": profile["label"], "status": status,
        "planned_episodes": doc["planned_episodes"], "provided_episodes": len(results),
        "missing_episodes": missing,
        "episodes": results,
        "quality_target": profile["min_human_score"],
        "scope": "studio policy qualification; not worldwide certification or artistic superiority",
    }
