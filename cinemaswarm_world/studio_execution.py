"""Operational local job transitions and reconciliation for production runtime.

A single production writer should persist each returned snapshot atomically.
Remote execution is not automatic and a valid provider receipt is not a visual
quality guarantee. All transitions are explicit and validate full state.
"""
from __future__ import annotations
import copy
from .studio_runtime import validate_runtime, _path, file_sha, _id
from .collaboration import digest, text

def ready_jobs(doc):
    validate_runtime(doc)
    states={job["id"]:job["state"] for job in doc["jobs"]}
    return [job["id"] for job in doc["jobs"] if job["state"]=="authorized"
            and all(states[dep]=="verified" for dep in job["dependencies"])]

def _locate(doc, job_id):
    _id(job_id, "job id")
    return next((j for j in doc["jobs"] if j["id"]==job_id), None)

def transition(doc, job_id, action, *, root=None, result=None):
    """Return new immutable snapshot. Caller must persist under a single-writer lock."""
    validate_runtime(doc)
    updated=copy.deepcopy(doc)
    job=_locate(updated,job_id)
    if job is None:
        raise ValueError("job not found")
    if action=="start":
        if job_id not in ready_jobs(doc):
            raise ValueError("job not authorized or prerequisites unverified")
        job["state"]="running"
    elif action=="reject":
        if job["state"] not in ("running","imported"):
            raise ValueError("only running or imported jobs may be rejected")
        job["state"]="rejected"
    elif action=="fail":
        if job["state"] not in ("running","imported"):
            raise ValueError("only running or imported jobs may fail")
        job["state"]="failed"
    elif action=="import":
        if job["state"]!="running" or root is None or not isinstance(result,dict):
            raise ValueError("import requires running job and source")
        required={"asset_id","source","canonical_ref","reviewer",
                  "provider_request_id","reported_cost_usd","provider_evidence"}
        if set(result)!=required:
            raise ValueError("invalid import result schema")
        asset_id=_id(result["asset_id"],"asset id")
        if any(a["id"]==asset_id for a in updated["assets"]):
            raise ValueError("output asset already registered")
        video=_path(root,result["source"])
        asset_hash=file_sha(video)
        text(result["reviewer"],"reviewer")
        text(result["canonical_ref"],"canonical_ref")
        text(result["provider_evidence"],"provider evidence")
        text(result["provider_request_id"],"provider request")
        reported=result["reported_cost_usd"]
        if type(reported) not in (int,float) or not 0<=reported<=job["estimated_cost_usd"]:
            raise ValueError("provider charge exceeds authorized job estimate")
        asset={"id":asset_id,"kind":job["kind"],"path":result["source"],
               "sha256":asset_hash,"approved":True,
               "reviewer":result["reviewer"],
               "canonical_ref":result["canonical_ref"],"origin_job":job_id}
        updated["assets"].append(asset)
        job["output_asset"]=asset_id
        job["actual_cost_usd"]=reported
        job["provider_receipt"]={
            "provider_request_id":result["provider_request_id"],
            "input_sha256s":[i["sha256"] for i in job["inputs"]],
            "output_sha256":asset_hash,"cost_usd":reported,
            "evidence":result["provider_evidence"]}
        job["state"]="imported"
    elif action=="verify":
        if job["state"]!="imported" or not isinstance(result,dict):
            raise ValueError("verify needs imported output and quality report")
        if set(result) != {"media_report","performance_approved","semantic_approved",
                           "reviewer","evidence"}:
            raise ValueError("invalid verification schema")
        text(result["reviewer"],"verification reviewer")
        text(result["evidence"],"verification evidence")
        qc=result["media_report"]
        if (not isinstance(qc,dict) or qc.get("status")!="checks_passed"
            or qc.get("error_count")!=0
            or qc.get("measurements",{}).get("sha256") !=
            next(a["sha256"] for a in updated["assets"] if a["id"]==job["output_asset"])):
            raise ValueError("verified media must pass independent measured stream gate")
        if result["performance_approved"] is not True or result["semantic_approved"] is not True:
            raise ValueError("performance and semantic approval required")
        job["state"]="verified"
    else:
        raise ValueError("unsupported job transition")
    validate_runtime(updated)
    return updated

def acceptance_report(doc):
    validate_runtime(doc)
    statuses={j["state"] for j in doc["jobs"]}
    generated=[j for j in doc["jobs"] if j["kind"]=="video"]
    passed=bool(generated) and all(j["state"]=="verified" for j in generated)
    return {"version":1,"episode_id":doc["episode_id"],
            "runtime_sha256":digest(doc),
            "status":"checks_passed" if passed else "incomplete",
            "verified_video_jobs":[j["id"] for j in generated if j["state"]=="verified"],
            "pending_video_jobs":[j["id"] for j in generated if j["state"]!="verified"],
            "scope":"video assets reconciled to provider receipts and reviewed media QC; does not independently verify narrative quality"}
