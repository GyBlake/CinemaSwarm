"""Unified proof refuses to call incomplete software or synthetic media fulfillment."""
import json
import subprocess
import sys
from pathlib import Path
from cinemaswarm_world.studio_runtime import file_sha,make_job
from cinemaswarm_world.fulfillment_audit import audit_fulfillment,STAGES

def test_unbuilt_project_not_falsely_fulfilled(tmp_path):
    (tmp_path/"approved.png").write_bytes(b"test")
    sha=file_sha(tmp_path/"approved.png")
    manifest={"version":1,
         "runtime":{"version":1,"episode_id":"pilot","visibility":"public",
           "budget_limit_usd":2.0,
           "assets":[{"id":"ref","kind":"image","path":"approved.png",
                      "sha256":sha,"approved":True,"reviewer":"test",
                      "canonical_ref":"face","origin_job":None}],
           "jobs":[make_job("pilot","shot1","video","heygen-video-1",
                       [{"asset_id":"ref","sha256":sha}],"a"*64,1.0,"test")],
           "checkpoints":[]},
         "media_qc":{"version":1,"episode_id":"pilot","clips":[]},
         "season_ledger":{"version":1,"season_id":"pilot-season",
              "episodes":[{"number":1,"id":"pilot","canon_sha256":"a"*64,
                          "approved":True}],
              "obligations":[]},
         "season_benchmark":None}
    report=audit_fulfillment(manifest,tmp_path)
    assert report["status"]=="unfulfilled"
    assert report["passed_stages"]<7
    assert report["stages"]["shared_asset_memory"]["status"]=="checks_passed"
    assert report["stages"]["provider_execution"]["status"]=="incomplete"
    assert report["stages"]["independent_media_qc"]["status"]=="blocked"
    assert report["stages"]["reviewed_multiepisode_delivery"]["status"]=="incomplete"

def test_cli_returns_nonzero_with_detailed_report(tmp_path):
    doc={"version":1,
         "runtime":{"version":1,"episode_id":"pilot","visibility":"public",
                    "budget_limit_usd":0,"assets":[],"jobs":[],"checkpoints":[]},
         "media_qc":{"version":1,"episode_id":"pilot","clips":[]},
         "season_ledger":{"version":1,"season_id":"single",
                 "episodes":[{"number":1,"id":"pilot","canon_sha256":"a"*64,
                             "approved":True}],"obligations":[]},
         "season_benchmark":None}
    (tmp_path/"proof.json").write_text(json.dumps(doc))
    script=Path(__file__).resolve().parents[1]/"cinema_swarm.py"
    proc=subprocess.run([sys.executable,str(script),"--audit-fulfillment",
                         "proof.json","--fulfillment-root",str(tmp_path),
                         "--fulfillment-report","audit.json"],cwd=tmp_path,
                        capture_output=True,text=True)
    assert proc.returncode==3,proc.stderr
    result=json.loads((tmp_path/"audit.json").read_text())
    assert result["status"]=="unfulfilled"
    assert list(result["stages"])==list(STAGES)
