"""Episode assembly tests: preflight, approvals, and real ffmpeg smoke."""
import json
import shutil
import subprocess
import sys
import wave
from pathlib import Path

import pytest
from PIL import Image
from cinemaswarm_world.episode_renderer import validate_plan, render_episode
from tests.gate_fixtures import write_gate


def create(tmp_path, mode="preview"):
    Image.new("RGB", (24, 40), "navy").save(tmp_path / "frame.png")
    doc = {"version": 1, "episode_id": "lantern-01",
           "profile": "smoke-vertical-v1", "mode": mode,
           "scenes": [
               {"scene_id": "opening", "image_source": "frame.png", "duration_seconds": 1.0},
               {"scene_id": "turn", "image_source": "frame.png", "duration_seconds": 1.0},
           ]}
    if mode == "candidate":
        (tmp_path / "qc.json").write_text(json.dumps(
            {"status": "checks_passed", "error_count": 0, "unknown_count": 0}))
        for scene in doc["scenes"]:
            scene.update(approved=True, continuity_report="qc.json")
        with wave.open(str(tmp_path / "voice.wav"), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(48000)
            wav.writeframes(b"\x00\x00" * 48000)
        (tmp_path / "captions.srt").write_text(
            "1\n00:00:00,000 --> 00:00:01,000\nLantern City\n")
        doc["audio_source"] = "voice.wav"
        doc["captions_source"] = "captions.srt"
        doc.update(write_gate(tmp_path, doc["episode_id"]))
    return doc


def test_invalid_scene_and_duration_rejected(tmp_path):
    plan = create(tmp_path)
    plan["scenes"][1]["scene_id"] = "opening"
    with pytest.raises(ValueError, match="duplicate"):
        validate_plan(plan)
    plan["scenes"][1]["scene_id"] = "turn"
    plan["scenes"][0]["duration_seconds"] = float("nan")
    with pytest.raises(ValueError, match="duration"):
        validate_plan(plan)


def test_candidate_requires_approved_continuity_and_assets(tmp_path):
    plan = create(tmp_path, "candidate")
    plan["scenes"][0]["approved"] = False
    with pytest.raises(ValueError, match="approval"):
        validate_plan(plan)
    plan["scenes"][0]["approved"] = True
    (tmp_path / "qc.json").write_text(json.dumps(
        {"status": "partial_evidence", "error_count": 0, "unknown_count": 1}))
    with pytest.raises(ValueError, match="continuity"):
        render_episode(plan, tmp_path, tmp_path / "out.mp4", tmp_path / "receipt.json")


@pytest.mark.skipif(not (shutil.which("ffmpeg") and shutil.which("ffprobe")),
                    reason="FFmpeg and FFprobe required for executable smoke test")
def test_real_episode_assembly_and_receipt(tmp_path):
    plan = create(tmp_path)
    master, receipt = tmp_path / "render.mp4", tmp_path / "receipt.json"
    output = render_episode(plan, tmp_path, master, receipt)
    assert output["status"] == "technical_assembly_only"
    assert output["quality_evaluation"] == "not_performed"
    assert output["audio"]["silence_generated"]
    assert output["inspected"]["width"] == 360
    assert output["inspected"]["height"] == 640
    assert abs(output["inspected"]["duration_seconds"] - 2) < 0.2
    assert master.is_file()
    assert json.loads(receipt.read_text())["master_sha256"] == output["master_sha256"]
    with pytest.raises(ValueError, match="exists"):
        render_episode(plan, tmp_path, master, receipt)


@pytest.mark.skipif(not (shutil.which("ffmpeg") and shutil.which("ffprobe")),
                    reason="FFmpeg and FFprobe required")
def test_real_candidate_render_provides_inputs_not_pretend_quality(tmp_path):
    plan = create(tmp_path, "candidate")
    output = render_episode(plan, tmp_path, tmp_path / "master.mp4", tmp_path / "receipt.json")
    assert not output["season_release_qualified"]
    assert not output["audio"]["silence_generated"]
    assert output["captions"]["author_provided"]
    assert len(output["scene_approvals"]) == 3


def test_source_traversal_rejected(tmp_path):
    plan = create(tmp_path)
    plan["scenes"][0]["image_source"] = "../missing.jpg"
    with pytest.raises((OSError, ValueError)):
        render_episode(plan, tmp_path, tmp_path / "out.mp4", tmp_path / "receipt.json")


@pytest.mark.skipif(not (shutil.which("ffmpeg") and shutil.which("ffprobe")),
                    reason="FFmpeg and FFprobe required")
def test_cli_episode_render_smoke(tmp_path):
    plan = create(tmp_path)
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan))
    cli = Path(__file__).resolve().parents[1] / "cinema_swarm.py"
    r = subprocess.run([sys.executable, str(cli), "--render-episode", str(path),
                        "--render-assets-root", str(tmp_path),
                        "--episode-master", str(tmp_path / "master.mp4"),
                        "--episode-receipt", str(tmp_path / "receipt.json")],
                       cwd=tmp_path, capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "master.mp4").is_file()
