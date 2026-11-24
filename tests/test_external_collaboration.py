"""External agent hydration and voice routing gates."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import pytest
from tests.gate_fixtures import write_gate
from cinemaswarm_world.collaboration import (
    validate_package, make_handoff, validate_acknowledgment, digest, load_json)
from cinemaswarm_world.performance import audit_performance
from cinemaswarm_world.episode_renderer import validate_plan, render_episode

def sample(root):
    write_gate(root)
    return (load_json(root / "collaboration.json"), load_json(root / "ack.json"),
            load_json(root / "takes.json"))

def test_handoff_digest_and_human_approval(tmp_path):
    p,a,_=sample(tmp_path)
    assert make_handoff(p)["package_sha256"] == digest(p)
    assert validate_acknowledgment(p,a)["status"] == "checks_passed"
    a["package_sha256"] = "0"*64
    with pytest.raises(ValueError, match="match"):
        validate_acknowledgment(p,a)

def test_unresolved_creative_intent_blocks(tmp_path):
    p,a,_=sample(tmp_path)
    a["unknowns"] = ["unclear betrayal motivation"]
    with pytest.raises(ValueError, match="unresolved"):
        validate_acknowledgment(p,a)
    a["unknowns"] = []
    a["human_approved"] = False
    with pytest.raises(ValueError, match="human approval"):
        validate_acknowledgment(p,a)

def test_voice_id_and_mouth_assignment_locked(tmp_path):
    p,_,_=sample(tmp_path)
    p["dialogue"][0]["voice_id"] = "wrong"
    with pytest.raises(ValueError, match="voice diverges"):
        validate_package(p)
    p["dialogue"][0]["voice_id"] = "approved-voice-mara-v1"
    p["dialogue"][0]["visible_character_id"] = "other"
    with pytest.raises(ValueError, match="speaking character"):
        validate_package(p)

@pytest.mark.parametrize("channel", ["thought","crowd","offscreen","disembodied"])
def test_nonvisual_voice_cannot_animate_mouth(tmp_path, channel):
    p,_,_=sample(tmp_path)
    p["dialogue"][0]["channel"] = channel
    with pytest.raises(ValueError, match="must not animate"):
        validate_package(p)
    p["dialogue"][0]["visible_character_id"] = None
    assert validate_package(p)

def test_voice_preview_must_be_approved(tmp_path):
    p,_,_=sample(tmp_path)
    p["characters"][0]["voice_approved"] = False
    with pytest.raises(ValueError, match="approval"):
        validate_package(p)

def test_unreviewed_take_and_lipsync_error_block(tmp_path):
    p,_,takes=sample(tmp_path)
    takes["takes"]=[]
    report=audit_performance(p,takes,tmp_path)
    assert report["status"] == "incomplete"
    assert "missing_take:line-1" in report["unknowns"]
    takes=load_json(tmp_path/"takes.json")
    takes["takes"][0]["sync_offset_ms"] = 120
    assert audit_performance(p,takes,tmp_path)["status"] == "blocked"

def test_wrong_voice_or_tampered_audio_fails(tmp_path):
    p,_,takes=sample(tmp_path)
    takes["takes"][0]["voice_id"] = "other-voice"
    assert audit_performance(p,takes,tmp_path)["status"] == "blocked"
    takes["takes"][0]["voice_id"] = p["characters"][0]["voice_id"]
    (tmp_path/"voice.wav").write_bytes(b"modified")
    assert any("audio_integrity_mismatch" in f for f in audit_performance(p,takes,tmp_path)["failures"])

def test_candidate_requires_preflight_receipts(tmp_path):
    from PIL import Image
    Image.new("RGB", (24,40)).save(tmp_path/"frame.png")
    plan={"version":1,"episode_id":"lantern-01","profile":"smoke-vertical-v1",
          "mode":"candidate","scenes":[{"scene_id":"opening","image_source":"frame.png",
          "duration_seconds":1,"approved":True,"continuity_report":"qc.json"}],
          "audio_source":"voice.wav","captions_source":"captions.srt"}
    with pytest.raises(ValueError, match="collaboration_package"):
        validate_plan(plan)
    plan.update(write_gate(tmp_path))
    (tmp_path/"qc.json").write_text(json.dumps(
        {"status":"checks_passed","error_count":0,"unknown_count":0}))
    (tmp_path/"captions.srt").write_text("1\\n00:00:00,000 --> 00:00:01,000\\nHi\\n")
    report=load_json(tmp_path/"performance.json")
    report["status"]="blocked"
    (tmp_path/"performance.json").write_text(json.dumps(report))
    with pytest.raises(ValueError, match="performance quality"):
        render_episode(plan,tmp_path,tmp_path/"out.mp4",tmp_path/"receipt.json")

def test_cli_contract_and_performance_pipeline(tmp_path):
    p,_,_=sample(tmp_path)
    cli=Path(__file__).resolve().parents[1]/"cinema_swarm.py"
    commands=[
       ["--prepare-collaboration",str(tmp_path/"collaboration.json"),
        "--collaboration-output",str(tmp_path/"handoff.json")],
       ["--verify-collaboration",str(tmp_path/"collaboration.json"),
        "--collaboration-ack",str(tmp_path/"ack.json"),
        "--collaboration-report",str(tmp_path/"ack-check.json")],
       ["--audit-performance",str(tmp_path/"takes.json"),
        "--performance-package",str(tmp_path/"collaboration.json"),
        "--performance-root",str(tmp_path),
        "--performance-output",str(tmp_path/"performance-output.json")]
    ]
    for cmd in commands:
        result=subprocess.run([sys.executable,str(cli)]+cmd,cwd=tmp_path,
                              capture_output=True,text=True)
        assert result.returncode==0,result.stderr
    result=load_json(tmp_path/"performance-output.json")
    assert result["status"]=="checks_passed"
    assert result["package_sha256"]==digest(p)
