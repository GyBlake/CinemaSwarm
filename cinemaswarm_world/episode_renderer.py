"""Reproducible local episode assembly from approved or preview visual assets.

Not an AI video generator. FFmpeg stitches supplied still images, a provided
soundtrack or generated silence, and records an evidence-only master receipt.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile

from .benchmarks import probe_media

MAX_PLAN_BYTES = 2_000_000
MAX_SCENES = 120
MAX_DURATION = 1800
PROFILES = {
    "smoke-vertical-v1": {"width": 360, "height": 640, "fps": 12},
    "premium-vertical-v1": {"width": 1080, "height": 1920, "fps": 30},
}


def _label(value, name):
    if not isinstance(value, str) or not value.strip() or len(value) > 256:
        raise ValueError(f"invalid {name}")
    return value


def _input(root: Path, value: str, extensions: tuple[str, ...]) -> Path:
    name = Path(_label(value, "input path"))
    if name.is_absolute():
        raise ValueError("absolute source path forbidden")
    base = root.resolve(strict=True)
    source = (base / name).resolve(strict=True)
    if not source.is_relative_to(base) or not source.is_file():
        raise ValueError("source escapes asset root or is not a file")
    if source.suffix.lower() not in extensions:
        raise ValueError("unsupported source format")
    if source.stat().st_size > 100_000_000:
        raise ValueError("source file exceeds 100 MB")
    return source


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for piece in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(piece)
    return digest.hexdigest()


def validate_plan(doc: object) -> dict:
    if not isinstance(doc, dict) or doc.get("version") != 1:
        raise ValueError("episode render plan version must be 1")
    if set(doc) - {"version", "episode_id", "profile", "mode", "scenes",
                   "audio_source", "captions_source"}:
        raise ValueError("unsupported episode plan field")
    _label(doc.get("episode_id"), "episode_id")
    if doc.get("profile") not in PROFILES:
        raise ValueError("unsupported render profile")
    if doc.get("mode") not in ("preview", "candidate"):
        raise ValueError("mode must be preview or candidate")
    scenes = doc.get("scenes")
    if not isinstance(scenes, list) or not 1 <= len(scenes) <= MAX_SCENES:
        raise ValueError("episode requires 1 to 120 scenes")
    identifiers = set()
    total = 0.0
    for scene in scenes:
        if not isinstance(scene, dict) or set(scene) - {
            "scene_id", "image_source", "duration_seconds", "approved", "continuity_report"
        }:
            raise ValueError("invalid scene schema")
        scene_id = _label(scene.get("scene_id"), "scene_id")
        if scene_id in identifiers:
            raise ValueError("duplicate scene_id")
        identifiers.add(scene_id)
        _label(scene.get("image_source"), "image_source")
        duration = scene.get("duration_seconds")
        if type(duration) not in (float, int) or not math.isfinite(duration) or not 0.5 <= duration <= 180:
            raise ValueError("scene duration must be between 0.5 and 180 seconds")
        total += duration
        if total > MAX_DURATION:
            raise ValueError("episode exceeds 1800 seconds")
        if doc["mode"] == "candidate":
            if scene.get("approved") is not True:
                raise ValueError("candidate scenes need explicit approval")
            _label(scene.get("continuity_report"), "continuity_report")
    for field in ("audio_source", "captions_source"):
        if field in doc:
            _label(doc[field], field)
    return doc


def load_plan(path: Path) -> dict:
    if path.stat().st_size > MAX_PLAN_BYTES:
        raise ValueError("episode plan exceeds 2 MB")
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("episode plan must be UTF-8 JSON") from exc
    return validate_plan(plan)


def _continuity(path: Path):
    if path.stat().st_size > MAX_PLAN_BYTES:
        raise ValueError("continuity report too large")
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid continuity report") from exc
    if (not isinstance(report, dict) or report.get("status") != "checks_passed"
        or report.get("error_count") != 0 or report.get("unknown_count") != 0):
        raise ValueError("candidate scene needs verified continuity report")
    return report


def render_episode(plan: dict, root: Path, output: Path, receipt_path: Path,
                   overwrite: bool = False) -> dict:
    """Render an MP4 and a receipt. Neither constitutes artistic qualification."""
    validate_plan(plan)
    if output.suffix.lower() != ".mp4" or receipt_path.suffix.lower() != ".json":
        raise ValueError("episode output must be MP4 and receipt must be JSON")
    if output.resolve() == receipt_path.resolve():
        raise ValueError("output and receipt cannot coincide")
    if not overwrite and (output.exists() or receipt_path.exists()):
        raise ValueError("output or receipt already exists; explicit overwrite required")
    profile = PROFILES[plan["profile"]]
    sources, approvals = [], []
    for scene in plan["scenes"]:
        source = _input(root, scene["image_source"], (".png", ".jpg", ".jpeg", ".webp"))
        sources.append(source)
        if plan["mode"] == "candidate":
            qc = _input(root, scene["continuity_report"], (".json",))
            _continuity(qc)
            approvals.append({"scene_id": scene["scene_id"],
                              "continuity_sha256": _hash(qc)})
    audio = _input(root, plan["audio_source"], (".wav", ".flac")) if plan.get("audio_source") else None
    captions = _input(root, plan["captions_source"], (".srt", ".vtt")) if plan.get("captions_source") else None
    if plan["mode"] == "candidate" and (audio is None or captions is None):
        raise ValueError("candidate requires an actual soundtrack and captions")
    if captions and not captions.read_text(encoding="utf-8").strip():
        raise ValueError("captions cannot be empty")
    total = sum(float(x["duration_seconds"]) for x in plan["scenes"])
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y"]
    filters = []
    for i, scene in enumerate(plan["scenes"]):
        duration = float(scene["duration_seconds"])
        command += ["-loop", "1", "-framerate", str(profile["fps"]),
                    "-t", f"{duration:.6f}", "-i", str(sources[i])]
        filters.append(
            f"[{i}:v]scale={profile['width']}:{profile['height']}:"
            "force_original_aspect_ratio=decrease,"
            f"pad={profile['width']}:{profile['height']}:(ow-iw)/2:(oh-ih)/2,"
            f"setsar=1,fps={profile['fps']},trim=duration={duration:.6f},"
            f"setpts=PTS-STARTPTS[v{i}]"
        )
    if audio:
        command += ["-i", str(audio)]
    else:
        command += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"]
    labels = "".join(f"[v{i}]" for i in range(len(sources)))
    filters.append(f"{labels}concat=n={len(sources)}:v=1:a=0,format=yuv420p[v]")
    command += [
        "-filter_complex", ";".join(filters), "-map", "[v]",
        "-map", f"{len(sources)}:a:0", "-af", "aresample=48000,apad",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
        "-pix_fmt", "yuv420p", "-r", str(profile["fps"]),
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-t", f"{total:.6f}", "-movflags", "+faststart",
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".cinemaswarm-", suffix=".mp4",
                                                  dir=output.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        try:
            result = subprocess.run(command + [str(temporary)], capture_output=True,
                                    text=True, timeout=600, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ValueError("ffmpeg unavailable or exceeded render timeout") from exc
        if result.returncode != 0:
            raise ValueError("ffmpeg episode assembly failed: " + result.stderr[-500:])
        inspected = probe_media(temporary)
        frame_tolerance = max(0.12, 2.0 / profile["fps"])
        if (inspected["width"], inspected["height"]) != (profile["width"], profile["height"]):
            raise ValueError("render dimensions differ from approved profile")
        if abs(inspected["duration_seconds"] - total) > frame_tolerance:
            raise ValueError("render duration differs from timeline budget")
        receipt = {
            "version": 1, "episode_id": plan["episode_id"], "profile": plan["profile"],
            "mode": plan["mode"], "status": "technical_assembly_only",
            "planned_duration_seconds": total, "inspected": inspected,
            "master_sha256": _hash(temporary), "master": str(output),
            "input_sha256": [
                {"scene_id": scene["scene_id"], "image_sha256": _hash(source),
                 "duration_seconds": scene["duration_seconds"]}
                for scene, source in zip(plan["scenes"], sources)
            ], "audio": {"source_sha256": _hash(audio) if audio else None,
                         "silence_generated": audio is None},
            "captions": {"source_sha256": _hash(captions) if captions else None,
                         "author_provided": captions is not None},
            "scene_approvals": approvals, "quality_evaluation": "not_performed",
            "season_release_qualified": False,
            "note": "Renderer assembles supplied art. No AI motion, voice, face or rights quality approval.",
        }
        if not overwrite and (output.exists() or receipt_path.exists()):
            raise ValueError("output or receipt appeared during rendering")
        os.replace(temporary, output)
        mode = "w" if overwrite else "x"
        with receipt_path.open(mode, encoding="utf-8") as stream:
            json.dump(receipt, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        return receipt
    finally:
        temporary.unlink(missing_ok=True)
