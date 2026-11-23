"""Season benchmark policy: fail-closed, real-media probe, completeness and rights."""
import hashlib
import json
from pathlib import Path
from unittest.mock import patch
import pytest

from cinemaswarm_world.benchmarks import (
    PROFILES, audit_season, load_season_manifest, validate_season_manifest,
)

def sample(tmp_path):
    (tmp_path / "master.mp4").write_bytes(b"fake-media-for-mocked-ffprobe")
    (tmp_path / "subtitle.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n")
    (tmp_path / "qc.json").write_text(json.dumps({"status": "checks_passed", "error_count": 0, "unknown_count": 0}))
    (tmp_path / "provenance.json").write_text(json.dumps({
        "season_id": "season-1", "episode_number": 1, "approved": True,
        "assets_licensed": True, "type": "internal attestation",
    }))
    ep = {
        "number": 1, "master": "master.mp4",
        "master_sha256": hashlib.sha256((tmp_path / "master.mp4").read_bytes()).hexdigest(),
        "captions": "subtitle.srt",
        "captions_sha256": hashlib.sha256((tmp_path / "subtitle.srt").read_bytes()).hexdigest(),
        "continuity_report": "qc.json", "provenance_record": "provenance.json",
        "reviews": {key: {"score": 98, "reviewer": "reviewer-1",
                           "evidence": "artistic-panel-report", "approved": True}
                    for key in ("narrative", "performance", "visual_identity", "voice_identity", "cinematography")},
        "caption_review": {"approved": True},
        "rights_review": {"approved": True},
    }
    return {"version": 1, "season_id": "season-1", "profile": "vertical-premium-v1",
            "planned_episodes": 1, "episodes": [ep]}


PROBED = {
    "width": 1080, "height": 1920, "duration_seconds": 120,
    "fps": 30, "audio_sample_rate": 48000,
    "video_codec": "h264", "audio_codec": "aac",
    "method": "local ffprobe inspection",
}


def test_missing_audio_verification_is_not_a_pass(tmp_path):
    doc = sample(tmp_path)
    with patch("cinemaswarm_world.benchmarks.probe_media", return_value=PROBED):
        report = audit_season(doc, tmp_path)
    assert report["status"] == "incomplete"
    assert "loudness_unmeasured" in report["episodes"][0]["unknowns"]
    assert report["episodes"][0]["artistic_score"] == 98


def test_obvious_delivery_defects_block(tmp_path):
    doc = sample(tmp_path)
    bad = dict(PROBED, width=720, duration_seconds=20)
    with patch("cinemaswarm_world.benchmarks.probe_media", return_value=bad):
        result = audit_season(doc, tmp_path)
    assert result["status"] == "blocked"
    assert "duration_outside_profile" in result["episodes"][0]["failures"]
    assert "resolution_below_profile" in result["episodes"][0]["failures"]


def test_season_completeness_is_required(tmp_path):
    doc = sample(tmp_path)
    doc["planned_episodes"] = 3
    with patch("cinemaswarm_world.benchmarks.probe_media", return_value=PROBED):
        report = audit_season(doc, tmp_path)
    assert report["missing_episodes"] == [2, 3]
    assert report["status"] == "incomplete"


def test_wrong_master_hash_blocks(tmp_path):
    doc = sample(tmp_path)
    doc["episodes"][0]["master_sha256"] = "0" * 64
    with patch("cinemaswarm_world.benchmarks.probe_media", return_value=PROBED):
        report = audit_season(doc, tmp_path)
    assert "master_hash_mismatch" in report["episodes"][0]["failures"]


def test_perceptual_score_cannot_override_critical_defect(tmp_path):
    doc = sample(tmp_path)
    doc["episodes"][0]["reviews"]["voice_identity"]["score"] = 84
    with patch("cinemaswarm_world.benchmarks.probe_media", return_value=PROBED):
        report = audit_season(doc, tmp_path)
    assert report["status"] == "blocked"
    assert "critical_artistic_dimension_below_floor" in report["episodes"][0]["failures"]


def test_invalid_review_without_human_approval_rejected(tmp_path):
    doc = sample(tmp_path)
    doc["episodes"][0]["reviews"]["performance"]["approved"] = False
    with pytest.raises(ValueError, match="approved"):
        validate_season_manifest(doc)


def test_path_traversal_is_not_accepted(tmp_path):
    doc = sample(tmp_path)
    doc["episodes"][0]["captions"] = "../secret.srt"
    with patch("cinemaswarm_world.benchmarks.probe_media", return_value=PROBED):
        report = audit_season(doc, tmp_path)
    assert "caption_file_unavailable" in report["episodes"][0]["unknowns"]


def test_unknown_benchmark_profile_fails_closed(tmp_path):
    doc = sample(tmp_path)
    doc["profile"] = "worldwide-certified"
    with pytest.raises(ValueError, match="unknown benchmark profile"):
        validate_season_manifest(doc)


def test_manifest_roundtrip(tmp_path):
    doc = sample(tmp_path)
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(doc))
    assert load_season_manifest(path) == doc


def test_real_ffprobe_schema_parser(monkeypatch, tmp_path):
    from cinemaswarm_world.benchmarks import probe_media
    class Result:
        returncode = 0
        stdout = json.dumps({"format": {"duration": "95.2"}, "streams": [
            {"codec_type": "video", "width": 1080, "height": 1920,
             "codec_name": "h264", "avg_frame_rate": "30000/1001"},
            {"codec_type": "audio", "codec_name": "aac", "sample_rate": "48000"},
        ]})
    monkeypatch.setattr("subprocess.run", lambda *a, **k: Result())
    assert probe_media(tmp_path / "master.mp4")["fps"] > 29
