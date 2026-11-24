"""Executable state machine covers actual import, verification, and targeted repair."""
import json
from pathlib import Path
import pytest
from cinemaswarm_world.collaboration import digest
from cinemaswarm_world.studio_runtime import file_sha, make_job, plan_repair
from cinemaswarm_world.studio_execution import ready_jobs, transition, acceptance_report

def fixture(tmp_path):
    (tmp_path/"face.png").write_bytes(b"approved preview")
    a={"id":"face","kind":"image","path":"face.png",
       "sha256":file_sha(tmp_path/"face.png"),"approved":True,
       "reviewer":"reviewer","canonical_ref":"face-v1","origin_job":None}
    j=make_job("proof","video-1","video","heygen-video-1",
       [{"asset_id":"face","sha256":a["sha256"]}],
       "a"*64,8.0,"studio")
    return {"version":1,"episode_id":"proof","visibility":"public",
            "budget_limit_usd":16.0,"assets":[a],"jobs":[j],"checkpoints":[]}

def test_ready_and_start_transition(tmp_path):
    doc=fixture(tmp_path)
    assert ready_jobs(doc)==["video-1"]
    started=transition(doc,"video-1","start")
    assert started["jobs"][0]["state"]=="running"
    assert doc["jobs"][0]["state"]=="authorized"
    assert ready_jobs(started)==[]

def test_real_file_import_receipt_and_measured_approval(tmp_path):
    doc=transition(fixture(tmp_path),"video-1","start")
    (tmp_path/"take.mp4").write_bytes(b"synthetic media fixture")
    imported=transition(doc,"video-1","import",root=tmp_path,
       result={"asset_id":"take","source":"take.mp4","canonical_ref":"proof-take1",
               "reviewer":"editor","provider_request_id":"remote-request-123",
               "reported_cost_usd":6.0,"provider_evidence":"test provider output"})
    assert imported["jobs"][0]["state"]=="imported"
    assert imported["jobs"][0]["provider_receipt"]["output_sha256"]==file_sha(tmp_path/"take.mp4")
    assert acceptance_report(imported)["status"]=="incomplete"
    approval={"media_report":{"status":"checks_passed","error_count":0,
               "measurements":{"sha256":file_sha(tmp_path/"take.mp4")}},
              "performance_approved":True,"semantic_approved":True,
              "reviewer":"editor","evidence":"test review (not a real media check)"}
    verified=transition(imported,"video-1","verify",result=approval)
    assert acceptance_report(verified)["status"]=="checks_passed"
    approval["performance_approved"]=False
    with pytest.raises(ValueError,match="performance"):
        transition(imported,"video-1","verify",result=approval)

def test_import_protects_overspend_and_path(tmp_path):
    doc=transition(fixture(tmp_path),"video-1","start")
    (tmp_path/"take.mp4").write_bytes(b"data")
    result={"asset_id":"take","source":"take.mp4","canonical_ref":"one",
            "reviewer":"editor","provider_request_id":"request",
            "reported_cost_usd":9.0,"provider_evidence":"test"}
    with pytest.raises(ValueError,match="exceeds"):
        transition(doc,"video-1","import",root=tmp_path,result=result)
    result["reported_cost_usd"]=4
    result["source"]="../bad.mp4"
    with pytest.raises(ValueError,match="outside"):
        transition(doc,"video-1","import",root=tmp_path,result=result)

def test_reject_then_repair_and_respect_budget(tmp_path):
    doc=transition(fixture(tmp_path),"video-1","start")
    failed=transition(doc,"video-1","reject")
    repaired=plan_repair(failed,"video-1","video-1-retry","supervisor")
    assert repaired["assets"]==failed["assets"]
    assert ready_jobs(repaired)==["video-1-retry"]
    assert repaired["jobs"][0]["state"]=="rejected"
    assert repaired["jobs"][1]["attempt"]==2

def test_missing_verified_dependency_never_runs(tmp_path):
    doc=fixture(tmp_path)
    second=make_job("proof","edit-1","edit","editor",
        [],"a"*64,1,"studio",dependencies=["video-1"])
    doc["jobs"].append(second)
    assert ready_jobs(doc)==["video-1"]
    with pytest.raises(ValueError,match="prerequisites"):
        transition(doc,"edit-1","start")
