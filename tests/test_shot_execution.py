"""Shot-contract mapping, cross-agent stage handoffs and release gate regression."""
import copy
import subprocess
import sys
from pathlib import Path
import pytest
from tests.gate_fixtures import write_gate
from cinemaswarm_world.collaboration import load_json, digest
from cinemaswarm_world.shot_execution import (
    validate_shots, stage_handoffs, audit_shot_evidence)

def sample(tmp_path):
    write_gate(tmp_path)
    package=load_json(tmp_path/"collaboration.json")
    semantic=load_json(tmp_path/"semantic.json")
    symbolic=load_json(tmp_path/"symbolic.json")
    graph=load_json(tmp_path/"production-graph.json")
    shots=load_json(tmp_path/"shot-contract.json")
    reviews=load_json(tmp_path/"shot-reviews.json")
    return package,semantic,symbolic,graph,shots,reviews

def test_canonical_shot_contract_and_stage_projection(tmp_path):
    pkg,sem,sym,graph,shots,reviews=sample(tmp_path)
    assert validate_shots(shots,pkg,sem,sym,graph)
    projection=stage_handoffs(shots,pkg,sem,sym,graph)
    item=projection["shots"][0]
    assert item["ordered_asset_refs"][0]["object_id"]=="storyboard"
    assert item["dialogue"][0]["voice_id"]=="approved-voice-mara-v1"
    assert item["symbolic_directions"][0]["reveal_policy"]=="conceal"
    assert "image" in item["stage_semantics"]
    assert audit_shot_evidence(shots,pkg,sem,sym,graph,reviews)["status"]=="checks_passed"

def test_stale_character_asset_blocks(tmp_path):
    pkg,sem,sym,graph,shots,reviews=sample(tmp_path)
    shots["shots"][0]["asset_refs"][0]["sha256"]="0"*64
    with pytest.raises(ValueError,match="stale"):
        validate_shots(shots,pkg,sem,sym,graph)

def test_wrong_speaker_and_dropped_dialogue_block(tmp_path):
    pkg,sem,sym,graph,shots,reviews=sample(tmp_path)
    shots["shots"][0]["cast"]=[]
    with pytest.raises(ValueError,match="active speaker"):
        validate_shots(shots,pkg,sem,sym,graph)
    shots["shots"][0]["cast"]=["mara"]
    shots["shots"][0]["dialogue_ids"]=[]
    with pytest.raises(ValueError,match="all dialogue"):
        validate_shots(shots,pkg,sem,sym,graph)

def test_dropped_symbolism_blocks(tmp_path):
    pkg,sem,sym,graph,shots,reviews=sample(tmp_path)
    shots["shots"][0]["symbolic_beat_ids"]=[]
    with pytest.raises(ValueError,match="all symbolic beats"):
        validate_shots(shots,pkg,sem,sym,graph)

def test_wrong_scene_or_timing_blocks(tmp_path):
    pkg,sem,sym,graph,shots,reviews=sample(tmp_path)
    shots["shots"][0]["end_ms"]=500
    with pytest.raises(ValueError,match="not scoped"):
        validate_shots(shots,pkg,sem,sym,graph)
    shots["shots"][0]["end_ms"]=2500
    with pytest.raises(ValueError,match="outside scene"):
        validate_shots(shots,pkg,sem,sym,graph)

def test_shot_requires_semantic_anchor(tmp_path):
    pkg,sem,sym,graph,shots,reviews=sample(tmp_path)
    shots["shots"][0]["semantic_projection_ids"]=[]
    with pytest.raises(ValueError,match="semantic"):
        validate_shots(shots,pkg,sem,sym,graph)

def test_handoff_detects_rewritten_canonical_digests(tmp_path):
    pkg,sem,sym,graph,shots,reviews=sample(tmp_path)
    shots["semantic_sha256"]="e"*64
    with pytest.raises(ValueError,match="stale"):
        validate_shots(shots,pkg,sem,sym,graph)

def test_unreviewed_or_failed_shot_cannot_pass(tmp_path):
    pkg,sem,sym,graph,shots,reviews=sample(tmp_path)
    reviews["reviews"]=[]
    assert audit_shot_evidence(shots,pkg,sem,sym,graph,reviews)["status"]=="incomplete"
    reviews=load_json(tmp_path/"shot-reviews.json")
    reviews["reviews"][0]["dialogue_binding_preserved"]=False
    report=audit_shot_evidence(shots,pkg,sem,sym,graph,reviews)
    assert report["status"]=="blocked"
    assert "opening-shot:dialogue_binding_preserved" in report["failures"]

def test_stale_review_digest_rejected(tmp_path):
    pkg,sem,sym,graph,shots,reviews=sample(tmp_path)
    shots["shots"][0]["camera"]="New approved framing"
    with pytest.raises(ValueError,match="not bound"):
        audit_shot_evidence(shots,pkg,sem,sym,graph,reviews)

def test_review_roundtrip_cli(tmp_path):
    pkg,sem,sym,graph,shots,reviews=sample(tmp_path)
    cli=Path(__file__).resolve().parents[1]/"cinema_swarm.py"
    common=["--prepare-shots",str(tmp_path/"shot-contract.json"),
            "--shot-package",str(tmp_path/"collaboration.json"),
            "--shot-semantic",str(tmp_path/"semantic.json"),
            "--shot-symbolic",str(tmp_path/"symbolic.json"),
            "--shot-graph",str(tmp_path/"production-graph.json")]
    for extra in (["--shot-output",str(tmp_path/"handoff.json")],
                  ["--shot-reviews",str(tmp_path/"shot-reviews.json"),
                   "--shot-output",str(tmp_path/"shot-check.json")]):
        proc=subprocess.run([sys.executable,str(cli),*common,*extra],
                            text=True,capture_output=True,cwd=tmp_path)
        assert proc.returncode==0,proc.stderr
    assert load_json(tmp_path/"shot-check.json")["status"]=="checks_passed"

def test_candidate_must_name_shot_contract(tmp_path):
    from cinemaswarm_world.episode_renderer import validate_plan
    plan={"version":1,"episode_id":"lantern-01","profile":"smoke-vertical-v1",
        "mode":"candidate","scenes":[{"scene_id":"opening",
             "image_source":"frame.png","duration_seconds":2,"approved":True,
             "continuity_report":"qc.json"}],
        "audio_source":"voice.wav","captions_source":"captions.srt",
        "collaboration_package":"collaboration.json","collaboration_ack":"ack.json",
        "performance_report":"performance.json","symbolic_program":"symbolic.json",
        "symbolic_report":"symbolic-report.json","production_graph":"production-graph.json",
        "production_graph_report":"production-report.json","semantic_contract":"semantic.json",
        "semantic_report":"semantic-report.json"}
    with pytest.raises(ValueError,match="shot_contract"):
        validate_plan(plan)
