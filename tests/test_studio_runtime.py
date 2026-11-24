"""Seven-stage studio controls: durable assets, budget, repair, media and season."""
import copy
import json
import subprocess
import sys
from pathlib import Path
import pytest
from cinemaswarm_world.collaboration import digest
from cinemaswarm_world.studio_runtime import (
    validate_runtime, audit_runtime, make_job, plan_repair, file_sha, write_atomic)
from cinemaswarm_world.series_ledger import validate_season_ledger, audit_season_ledger

def doc(tmp_path):
    (tmp_path/"approved.png").write_bytes(b"approved synthetic reference")
    asset={"id":"mara-face","kind":"image","path":"approved.png",
           "sha256":file_sha(tmp_path/"approved.png"),"approved":True,
           "reviewer":"test reviewer","canonical_ref":"mara-v1","origin_job":None}
    job=make_job("pilot","shot-1","video","video-service",
                 [{"asset_id":"mara-face","sha256":asset["sha256"]}],
                 "a"*64,5.0,"authorized-test-editor")
    return {"version":1,"episode_id":"pilot","visibility":"public",
            "budget_limit_usd":15.0,"assets":[asset],"jobs":[job],"checkpoints":[]}

def test_preflight_validates_approved_inputs_and_budget(tmp_path):
    obj=doc(tmp_path)
    assert validate_runtime(obj)
    assert audit_runtime(obj,tmp_path)["status"]=="checks_passed"
    obj["budget_limit_usd"]=4.99
    with pytest.raises(ValueError,match="budget"):
        validate_runtime(obj)

def test_real_asset_change_fails_integrity(tmp_path):
    obj=doc(tmp_path)
    (tmp_path/"approved.png").write_bytes(b"tampered")
    assert audit_runtime(obj,tmp_path)["status"]=="blocked"

def test_stale_reference_blocks_provider_input(tmp_path):
    obj=doc(tmp_path)
    obj["jobs"][0]["inputs"][0]["sha256"]="f"*64
    with pytest.raises(ValueError,match="stale"):
        validate_runtime(obj)

def test_duplicate_retries_prevent_double_submission(tmp_path):
    obj=doc(tmp_path)
    obj["jobs"].append(copy.deepcopy(obj["jobs"][0]))
    with pytest.raises(ValueError,match="duplicate job"):
        validate_runtime(obj)
    obj["jobs"][1]["id"]="shot-2"
    with pytest.raises(ValueError,match="idempotent"):
        validate_runtime(obj)

def test_declared_provider_receipt_and_output_asset(tmp_path):
    obj=doc(tmp_path)
    video=tmp_path/"take.mp4"
    video.write_bytes(b"synthetic bytes, NOT playable video")
    item={"id":"take1","kind":"video","path":"take.mp4",
          "sha256":file_sha(video),"approved":True,"reviewer":"test",
          "canonical_ref":"take1-canon","origin_job":"shot-1"}
    obj["assets"].append(item)
    job=obj["jobs"][0]
    job.update(state="verified",output_asset="take1",actual_cost_usd=4.50,
               provider_receipt={"provider_request_id":"abc123",
                   "input_sha256s":[obj["assets"][0]["sha256"]],
                   "output_sha256":item["sha256"],
                   "cost_usd":4.50,"evidence":"test-only claimed provider record"})
    assert validate_runtime(obj)
    job["provider_receipt"]["input_sha256s"]=[]
    with pytest.raises(ValueError,match="input receipt"):
        validate_runtime(obj)

def test_failed_take_targeted_retry_preserves_assets(tmp_path):
    obj=doc(tmp_path)
    obj["jobs"][0]["state"]="rejected"
    repaired=plan_repair(obj,"shot-1","shot-1-retry","test-supervisor")
    assert len(repaired["jobs"])==2
    assert repaired["assets"]==obj["assets"]
    assert repaired["jobs"][1]["parent_job"]=="shot-1"
    assert repaired["jobs"][1]["attempt"]==2
    assert repaired["jobs"][1]["idempotency_key"]!=repaired["jobs"][0]["idempotency_key"]

def test_cannot_repair_unfailed_or_exceed_budget(tmp_path):
    obj=doc(tmp_path)
    with pytest.raises(ValueError,match="failed or rejected"):
        plan_repair(obj,"shot-1","retry","test")
    obj["jobs"][0]["state"]="failed"
    obj["budget_limit_usd"]=5
    with pytest.raises(ValueError,match="budget"):
        plan_repair(obj,"shot-1","retry","test")

def test_checkpoint_and_private_boundary(tmp_path):
    obj=doc(tmp_path)
    obj["checkpoints"]=[{"name":"assets","state_digest":digest(obj["assets"]),
                          "reviewer":"test","approved":True}]
    assert validate_runtime(obj)
    obj["assets"][0]["canonical_ref"]="dreamcorp-secret"
    with pytest.raises(ValueError,match="private"):
        validate_runtime(obj)

def season():
    return {"version":1,"season_id":"angel-season",
            "episodes":[{"number":i,"id":f"ep{i}",
                         "canon_sha256":"a"*64,"approved":True} for i in range(1,4)],
            "obligations":[{"id":"wings","concept_id":"angelic-wing-shadow",
                "introduced_in":1,"due_by":3,"resolved_in":None,
                "seed_evidence":"ep1 approved storyboards",
                "payoff_evidence":None,"approved":False}]}

def test_delayed_payoff_valid_until_due_then_blocked():
    item=season()
    assert validate_season_ledger(item)
    assert audit_season_ledger(item,through_episode=2)["status"]=="checks_passed"
    assert audit_season_ledger(item,through_episode=2)["pending"]==["wings"]
    assert audit_season_ledger(item,through_episode=3)["status"]=="blocked"
    item["obligations"][0].update(resolved_in=3,payoff_evidence="reviewed ep3",
                                  approved=True)
    assert audit_season_ledger(item)["status"]=="checks_passed"

def test_unapproved_payoff_and_invalid_chronology_fail():
    item=season()
    item["obligations"][0]["resolved_in"]=2
    with pytest.raises(ValueError,match="payoff evidence"):
        validate_season_ledger(item)
    item["obligations"][0].update(payoff_evidence="ep2 take",approved=True,
                                  resolved_in=4)
    with pytest.raises(ValueError,match="permitted timeline"):
        validate_season_ledger(item)

def test_atomic_persistence_no_silent_overwrite(tmp_path):
    dest=tmp_path/"runtime.json"
    obj=doc(tmp_path)
    write_atomic(dest,obj)
    assert json.loads(dest.read_text())==obj
    with pytest.raises(ValueError,match="overwrite"):
        write_atomic(dest,obj)
    write_atomic(dest,obj,overwrite=True)

def test_cli_full_ledger_and_runtime(tmp_path):
    obj=doc(tmp_path)
    (tmp_path/"runtime.json").write_text(json.dumps(obj))
    (tmp_path/"season.json").write_text(json.dumps(season()))
    cli=Path(__file__).resolve().parents[1]/"cinema_swarm.py"
    for args in (
        ["--audit-runtime",str(tmp_path/"runtime.json"),"--runtime-root",str(tmp_path),
         "--runtime-report",str(tmp_path/"runtime-report.json")],
        ["--audit-series-ledger",str(tmp_path/"season.json"),"--through-episode","2",
         "--series-report",str(tmp_path/"series-report.json")]):
        run=subprocess.run([sys.executable,str(cli),*args],text=True,
                           capture_output=True,cwd=tmp_path)
        assert run.returncode==0,run.stderr
    blocked=subprocess.run([sys.executable,str(cli),"--audit-series-ledger",
                            str(tmp_path/"season.json"),"--through-episode","3",
                            "--series-report",str(tmp_path/"blocked.json")],
                           text=True,capture_output=True,cwd=tmp_path)
    assert blocked.returncode==3
