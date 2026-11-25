"""CLI operations are offline by default, explicit transitions and cost approval."""
import json
import subprocess
import sys
from pathlib import Path
from cinemaswarm_world.studio_runtime import file_sha, make_job

SCRIPT=Path(__file__).resolve().parents[1]/"cinema_swarm.py"

def run(tmp_path,args):
    return subprocess.run([sys.executable,str(SCRIPT),*args],cwd=tmp_path,
                          capture_output=True,text=True)

def test_provider_dry_run_does_not_require_api_key(tmp_path):
    (tmp_path/"brief.txt").write_text("A woman stands in a backlit doorway.")
    p=run(tmp_path,["--provider-video-brief","brief.txt","--provider-video-plan","video-plan.json"])
    assert p.returncode==0,p.stderr
    doc=json.loads((tmp_path/"video-plan.json").read_text())
    assert doc["provider"]=="heygen-video-1"
    assert doc["request"]["prompt"]=="A woman stands in a backlit doorway."

def test_spend_command_requires_explicit_authorization(tmp_path):
    (tmp_path/"brief.txt").write_text("A wing-like illusion formed by two guards")
    assert run(tmp_path,["--provider-video-brief","brief.txt",
                         "--provider-video-plan","video-plan.json"]).returncode==0
    command=["--submit-provider-plan","video-plan.json",
             "--provider-receipt","sent.json",
             "--provider-approved-by","editor",
             "--provider-max-cost-usd","10",
             "--provider-estimated-cost-usd","2"]
    result=run(tmp_path,command)
    assert result.returncode==2
    assert "authorization" in result.stderr
    assert not (tmp_path/"sent.json").exists()

def test_ready_and_start_job_from_disk(tmp_path):
    (tmp_path/"asset.png").write_bytes(b"synthetic approved image")
    sha=file_sha(tmp_path/"asset.png")
    asset={"id":"ref","kind":"image","path":"asset.png","sha256":sha,
           "approved":True,"reviewer":"tester","canonical_ref":"ref-v1",
           "origin_job":None}
    job=make_job("pilot","video-1","video","heygen-video-1",
                 [{"asset_id":"ref","sha256":sha}],"a"*64,2,"tester")
    doc={"version":1,"episode_id":"pilot","visibility":"public",
         "budget_limit_usd":3,"assets":[asset],"jobs":[job],"checkpoints":[]}
    (tmp_path/"runtime.json").write_text(json.dumps(doc))
    p=run(tmp_path,["--list-ready-jobs","runtime.json"])
    assert p.returncode==0,p.stderr
    assert "video-1" in p.stdout
    p=run(tmp_path,["--job-event","runtime.json","--job-id","video-1",
                    "--job-action","start","--job-output","running.json"])
    assert p.returncode==0,p.stderr
    assert json.loads((tmp_path/"running.json").read_text())["jobs"][0]["state"]=="running"
