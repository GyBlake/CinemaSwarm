"""Production graph regression: explicit input lineage, cost receipts, and take approval."""
import copy
import json
import subprocess
import sys
from pathlib import Path
import pytest
from tests.gate_fixtures import write_gate
from cinemaswarm_world.collaboration import load_json
from cinemaswarm_world.production_graph import validate_graph, audit_graph, file_sha

def sample(root):
    write_gate(root)
    return load_json(root / "production-graph.json")

def test_valid_graph_and_take_lineage(tmp_path):
    doc=sample(tmp_path)
    assert validate_graph(doc)
    result=audit_graph(doc,tmp_path)
    assert result["status"] == "checks_passed"
    assert result["objects"][2]["input_ids"] == ["take1"]

def test_stale_reference_blocks_before_agent_submission(tmp_path):
    doc=sample(tmp_path)
    doc["objects"][1]["inputs_sent_in_order"][0]["sha256"]="0"*64
    with pytest.raises(ValueError,match="stale"):
        validate_graph(doc)

def test_forward_or_cyclic_input_reference_rejected(tmp_path):
    doc=sample(tmp_path)
    doc["objects"][0]["inputs_sent_in_order"]=[{"id":"take1","sha256":doc["objects"][1]["sha256"]}]
    with pytest.raises(ValueError,match="forward"):
        validate_graph(doc)

def test_unapproved_stop_blocks(tmp_path):
    doc=sample(tmp_path)
    doc["stops"]["takes_reviewed"]["approved"]=False
    with pytest.raises(ValueError,match="not approved"):
        validate_graph(doc)

def test_wrong_cut_references_block(tmp_path):
    doc=sample(tmp_path)
    doc["cut"]["take_ids"]=["storyboard"]
    with pytest.raises(ValueError,match="invalid take"):
        validate_graph(doc)

def test_provider_receipt_requires_matching_inputs_and_cost_approval(tmp_path):
    doc=sample(tmp_path)
    take=doc["objects"][1]
    take["receipt"]={"provider":"video-provider", "request_id":"req-0001",
       "output_sha256":take["sha256"],
       "input_sha256s_in_order":[doc["objects"][0]["sha256"]],
       "cost_usd":2.50, "cost_approved":True,"reviewer":"test"}
    assert validate_graph(doc)
    take["receipt"]["input_sha256s_in_order"]=["0"*64]
    with pytest.raises(ValueError,match="inputs differ"):
        validate_graph(doc)
    take["receipt"]["input_sha256s_in_order"]=[doc["objects"][0]["sha256"]]
    take["receipt"]["cost_approved"]=False
    with pytest.raises(ValueError,match="cost approval"):
        validate_graph(doc)

def test_tampered_output_detected(tmp_path):
    doc=sample(tmp_path)
    (tmp_path/"sample-take.txt").write_text("modified take")
    report=audit_graph(doc,tmp_path)
    assert report["status"]=="blocked"
    assert "take1:hash_mismatch" in report["failures"]

def test_relative_path_escape_blocked(tmp_path):
    doc=sample(tmp_path)
    doc["objects"][1]["source"]="../outside-take.mp4"
    assert "take1:file_unavailable" in audit_graph(doc,tmp_path)["failures"]

def test_reuse_does_not_duplicate_paid_call_history(tmp_path):
    doc=sample(tmp_path)
    first=audit_graph(doc,tmp_path)
    second=audit_graph(doc,tmp_path)
    assert first == second
    assert all(x["has_provider_receipt"] is False for x in second["objects"])

def test_public_private_boundary(tmp_path):
    doc=sample(tmp_path)
    doc["objects"][0]["id"]="dreamcorp-secret"
    with pytest.raises(ValueError,match="private context"):
        validate_graph(doc)

def test_cli_graph_audit_and_nonzero_on_tamper(tmp_path):
    doc=sample(tmp_path)
    cli=Path(__file__).resolve().parents[1]/"cinema_swarm.py"
    def run():
        return subprocess.run([
            sys.executable,str(cli),"--audit-production-graph",
            str(tmp_path/"production-graph.json"),
            "--production-root",str(tmp_path),
            "--production-report",str(tmp_path/"report-new.json"),"--overwrite"],
            capture_output=True,text=True,cwd=tmp_path)
    r=run()
    assert r.returncode==0,r.stderr
    (tmp_path/"sample-cut.txt").write_text("tamper")
    r=run()
    assert r.returncode==3,r.stderr

def test_candidate_requires_graph_files(tmp_path):
    from cinemaswarm_world.episode_renderer import validate_plan
    doc={"version":1,"episode_id":"lantern-01","profile":"smoke-vertical-v1",
        "mode":"candidate","scenes":[{"scene_id":"s1","image_source":"frame.png",
        "duration_seconds":1,"approved":True,"continuity_report":"qc.json"}],
        "audio_source":"voice.wav","captions_source":"captions.srt",
        "collaboration_package":"collaboration.json","collaboration_ack":"ack.json",
        "performance_report":"performance.json","symbolic_program":"symbolic.json",
        "symbolic_report":"symbolic-report.json"}
    with pytest.raises(ValueError,match="production_graph"):
        validate_plan(doc)
