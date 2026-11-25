"""Semantic interoperability: intent, meaning, provenance, translation and release gates."""
import copy
import json
import subprocess
import sys
from pathlib import Path
import pytest
from tests.gate_fixtures import write_gate
from cinemaswarm_world.collaboration import load_json, digest
from cinemaswarm_world.semantic_interop import validate_semantics, make_projection, audit_semantics

def sample(root):
    write_gate(root)
    return (load_json(root/"collaboration.json"),
            load_json(root/"semantic.json"),
            load_json(root/"semantic-eval.json"))

def test_semantic_public_projection_includes_all_required_layers(tmp_path):
    pkg, contract, evidence=sample(tmp_path)
    projected=make_projection(contract,pkg)
    assert projected["contract_sha256"] == digest(contract)
    assert projected["layers"] == ["semantic","transport","execution","presentation"]
    assert audit_semantics(contract,pkg,evidence)["status"] == "checks_passed"

def test_digest_drift_not_accepted(tmp_path):
    pkg, contract, evidence=sample(tmp_path)
    pkg["creative_intent"]="changed without semantic reapproval"
    with pytest.raises(ValueError,match="stale"):
        validate_semantics(contract,pkg)

def test_contradictory_semantic_relations_rejected(tmp_path):
    pkg, contract, _=sample(tmp_path)
    other=copy.deepcopy(contract["concepts"][0])
    other["id"]="betrayal"
    contract["concepts"].append(other)
    contract["relations"]=[
        {"subject":"trust-custody","operator":"equivalent","object":"betrayal","rationale":"claimed same"},
        {"subject":"trust-custody","operator":"contradicts","object":"betrayal","rationale":"claimed opposite"},
    ]
    contract["projections"][0]["concept_ids"].append("betrayal")
    with pytest.raises(ValueError,match="conflict"):
        validate_semantics(contract,pkg)

def test_missing_semantic_projection_is_blocked(tmp_path):
    pkg, contract, evidence=sample(tmp_path)
    contract["concepts"].append({
        "id":"sacrifice","definition":"Surrender an object to save someone",
        "polarity":"safety versus loss","scene_id":"opening",
        "visibility":"public","evidence":"visible choice",
        "source_tradition":"original screenplay"
    })
    with pytest.raises(ValueError,match="unprojected"):
        validate_semantics(contract,pkg)

def test_private_markers_not_exported(tmp_path):
    pkg, contract, _=sample(tmp_path)
    contract["origin"]["intent"]="Send proprietary Imani Vale secret references"
    # Private name on its own should not be auto exported, but denylist catches
    # references to named private corpus.
    contract["origin"]["intent"]="Dreamcorp private ontology export"
    with pytest.raises(ValueError,match="private context"):
        validate_semantics(contract,pkg)

def test_unauthorized_reviewer_rejected(tmp_path):
    pkg, contract, _=sample(tmp_path)
    contract["review"]["approved"]=False
    with pytest.raises(ValueError,match="human approval"):
        validate_semantics(contract,pkg)

def test_semantic_drift_blocks(tmp_path):
    pkg,contract,evidence=sample(tmp_path)
    evidence["evaluations"][0]["meaning_preserved"]=False
    report=audit_semantics(contract,pkg,evidence)
    assert report["status"] == "blocked"
    assert report["error_count"] == 1

def test_unreviewed_or_missing_does_not_pass(tmp_path):
    pkg,contract,evidence=sample(tmp_path)
    evidence["evaluations"]=[]
    report=audit_semantics(contract,pkg,evidence)
    assert report["status"]=="incomplete"
    assert report["unknown_count"]==1

def test_contradiction_and_prohibition_fail(tmp_path):
    pkg,contract,evidence=sample(tmp_path)
    evidence["evaluations"][0]["contradiction_found"]=True
    assert audit_semantics(contract,pkg,evidence)["status"]=="blocked"
    evidence["evaluations"][0]["contradiction_found"]=False
    evidence["evaluations"][0]["prohibitions_respected"]=False
    assert audit_semantics(contract,pkg,evidence)["status"]=="blocked"

def test_candidate_requires_semantic_contract(tmp_path):
    from cinemaswarm_world.episode_renderer import validate_plan
    candidate={"version":1,"episode_id":"lantern-01","profile":"smoke-vertical-v1",
        "mode":"candidate","scenes":[{"scene_id":"s1","image_source":"frame.png",
        "duration_seconds":1,"approved":True,"continuity_report":"qc.json"}],
        "audio_source":"voice.wav","captions_source":"captions.srt",
        "collaboration_package":"collaboration.json","collaboration_ack":"ack.json",
        "performance_report":"performance.json","symbolic_program":"symbolic.json",
        "symbolic_report":"symbolic-report.json","production_graph":"production-graph.json",
        "production_graph_report":"production-report.json"}
    with pytest.raises(ValueError,match="semantic_contract"):
        validate_plan(candidate)

def test_cli_generate_and_audit(tmp_path):
    pkg,contract,evidence=sample(tmp_path)
    cli=Path(__file__).resolve().parents[1]/"cinema_swarm.py"
    commands=[
        ["--prepare-semantics",str(tmp_path/"semantic.json"),
         "--semantic-package",str(tmp_path/"collaboration.json"),
         "--semantic-output",str(tmp_path/"semantic-projection.json")],
        ["--audit-semantics",str(tmp_path/"semantic-eval.json"),
         "--semantic-contract",str(tmp_path/"semantic.json"),
         "--semantic-package",str(tmp_path/"collaboration.json"),
         "--semantic-output",str(tmp_path/"semantic-audit.json")]]
    for command in commands:
        r=subprocess.run([sys.executable,str(cli),*command],
                         cwd=tmp_path,capture_output=True,text=True)
        assert r.returncode==0,r.stderr
    assert load_json(tmp_path/"semantic-audit.json")["status"]=="checks_passed"

def test_rosetta_pivot_shared_across_agent_dialects(tmp_path):
    pkg, contract, evaluation = sample(tmp_path)
    first = contract["projections"][0]
    second = dict(first, id="edit-handoff", stage="editing",
                  direction="Retain the handoff as an act of trust through the cut",
                  output_contract="Editorial cut preserves motive")
    contract["projections"].append(second)
    assert validate_semantics(contract, pkg)
    projection = make_projection(contract, pkg)
    assert {tuple(p["concept_ids"]) for p in projection["authorized_projections"]} == {("trust-custody",)}
    assert {p["stage"] for p in projection["authorized_projections"]} == {"image", "editing"}
    evaluation["contract_sha256"] = digest(contract)
    evaluation["evaluations"].append(dict(
        evaluation["evaluations"][0], projection_id="edit-handoff"))
    assert audit_semantics(contract, pkg, evaluation)["status"] == "checks_passed"
    evaluation["evaluations"] = evaluation["evaluations"][:1]
    assert audit_semantics(contract, pkg, evaluation)["status"] == "incomplete"
