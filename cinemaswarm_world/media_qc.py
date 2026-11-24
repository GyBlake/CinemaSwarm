"""Non-biometric, local pixel/audio-stream inspection of real rendered video.

Measures real frames and ffprobe streams rather than treating declared approval
as sensed quality. Does not identify characters or assert perceptual lip sync.
"""
from __future__ import annotations
import json
import math
import subprocess
from pathlib import Path
from .studio_runtime import _path, file_sha

def inspect_clip(root, name, *, expected_sha256, min_duration=1, max_duration=180,
                 min_width=320, min_height=320, require_audio=True,
                 minimum_motion=0.25):
    video = _path(root, name)
    if video.suffix.lower() not in (".mp4", ".mov", ".mkv"):
        raise ValueError("unsupported video format")
    if not isinstance(expected_sha256, str) or len(expected_sha256) != 64:
        raise ValueError("expected media digest required")
    failures, measurements = [], {}
    actual = file_sha(video)
    measurements["sha256"] = actual
    if actual != expected_sha256:
        failures.append("video_hash_mismatch")
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration:stream=codec_type,width,height,r_frame_rate,sample_rate",
         "-of", "json", str(video)],
        capture_output=True, text=True, timeout=30, check=False)
    if probe.returncode:
        raise ValueError("ffprobe failed for local media")
    info = json.loads(probe.stdout)
    streams = info.get("streams", [])
    vs = next((s for s in streams if s.get("codec_type") == "video"), None)
    aud = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if not vs:
        raise ValueError("missing video stream")
    duration = float(info.get("format", {}).get("duration", 0))
    if not math.isfinite(duration):
        raise ValueError("invalid measured duration")
    measurements.update({"duration_seconds": duration, "width": vs["width"],
                         "height": vs["height"], "has_audio": bool(aud)})
    if not min_duration <= duration <= max_duration:
        failures.append("duration_out_of_bounds")
    if vs["width"] < min_width or vs["height"] < min_height:
        failures.append("resolution_below_minimum")
    if require_audio and aud is None:
        failures.append("audio_stream_missing")
    sample = subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin",
        "-i", str(video), "-vf", "fps=1,scale=48:48,format=gray",
        "-an", "-frames:v", "120", "-f", "rawvideo", "-pix_fmt", "gray", "-"
    ], capture_output=True, timeout=90, check=False)
    if sample.returncode:
        raise ValueError("frame extraction failed")
    bytes_per_frame = 48 * 48
    count = len(sample.stdout) // bytes_per_frame
    measurements["sampled_frames"] = count
    if count < 2:
        failures.append("insufficient_frames_to_measure_motion")
        motion = 0.0
    else:
        frames = [sample.stdout[i*bytes_per_frame:(i+1)*bytes_per_frame]
                  for i in range(count)]
        frame_changes = [
            sum(abs(a-b) for a, b in zip(frames[i],frames[i-1])) / bytes_per_frame
            for i in range(1,count)]
        motion = sum(frame_changes)/len(frame_changes)
        if motion < minimum_motion:
            failures.append("insufficient_temporal_pixel_change")
    measurements["mean_interframe_difference"] = round(motion, 5)
    measurements["motion_threshold"] = minimum_motion
    return {"version": 1, "status": "blocked" if failures else "checks_passed",
            "error_count": len(failures), "failures": failures,
            "measurements": measurements,
            "limitations": ["motion detects pixel changes, not acting quality",
                            "no face, voice identity or phoneme accuracy measured",
                            "requires independent human performance assessment"]}

def inspect_suite(doc, root):
    if not isinstance(doc, dict) or set(doc) != {"version", "episode_id", "clips"} or doc["version"] != 1:
        raise ValueError("invalid media QC manifest")
    clips = doc["clips"]
    if not isinstance(clips, list) or not clips or len(clips) > 120:
        raise ValueError("clips required")
    names, reports = set(), []
    for c in clips:
        if not isinstance(c, dict) or set(c) != {"id", "path", "sha256", "min_duration",
                                                  "max_duration", "min_width",
                                                  "min_height", "require_audio",
                                                  "minimum_motion"}:
            raise ValueError("invalid media QC clip")
        if c["id"] in names:
            raise ValueError("duplicate clip ID")
        names.add(c["id"])
        report = inspect_clip(root,c["path"],expected_sha256=c["sha256"],
                              min_duration=c["min_duration"],
                              max_duration=c["max_duration"],
                              min_width=c["min_width"], min_height=c["min_height"],
                              require_audio=c["require_audio"],
                              minimum_motion=c["minimum_motion"])
        reports.append({"clip_id":c["id"],**report})
    failures = sum(x["error_count"] for x in reports)
    return {"version":1,"episode_id":doc["episode_id"],
            "status":"blocked" if failures else "checks_passed",
            "error_count":failures,"clips":reports}
