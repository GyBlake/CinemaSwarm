"""Fail-closed end-to-end studio fulfillment audit.

No feature is called fulfilled solely because software exists or tests pass.
A seven-stage proof requires actual local media, independent FFmpeg inspection,
correct provider provenance, targeted repairs, paid-job governance and reviewed
multi-episode production evidence. No private AI agent assertions are made.
"""
from __future__ import annotations
from pathlib import Path
from .studio_runtime import validate_runtime, audit_runtime
from .studio_execution import acceptance_report
from .media_qc import inspect_suite
from .series_ledger import audit_season_ledger
from .benchmarks import audit_season

STAGES = (
    "provider_execution","shared_asset_memory","independent_media_qc",
    "targeted_repair","cross_episode_continuity",
    "durable_orchestration","reviewed_multiepisode_delivery"
)

def audit_fulfillment(manifest, root):
    if not isinstance(manifest,dict) or set(manifest) != {
         "version","runtime","media_qc","season_ledger","season_benchmark"} or manifest["version"]!=1:
        raise ValueError("invalid full studio proof manifest")
    root=Path(root)
    steps={k:{"status":"incomplete","evidence":[]} for k in STAGES}
    runtime=manifest["runtime"]
    runtime_ok=False
    try:
        validate_runtime(runtime)
        runtime_integrity=audit_runtime(runtime,root)
        if runtime_integrity["status"]=="checks_passed":
            runtime_ok=True
            if acceptance_report(runtime)["status"]=="checks_passed":
                steps["provider_execution"]={"status":"checks_passed",
                    "evidence":[j["id"] for j in runtime["jobs"]
                                if j["kind"]=="video" and j["state"]=="verified"]}
            if runtime["assets"] and all(a["approved"] for a in runtime["assets"]):
                steps["shared_asset_memory"]={"status":"checks_passed",
                    "evidence":[a["id"] for a in runtime["assets"]]}
            if any(j["parent_job"] is not None and j["state"]=="verified" and
                   any(k["id"]==j["parent_job"] and k["state"] in ("failed","rejected")
                       for k in runtime["jobs"]) for j in runtime["jobs"]):
                steps["targeted_repair"]={"status":"checks_passed",
                    "evidence":["verified repaired job with rejected/failed predecessor"]}
            if runtime["checkpoints"] and all(j["state"]!="running" for j in runtime["jobs"]):
                steps["durable_orchestration"]={"status":"checks_passed",
                    "evidence":["approved checkpoints, budget preflight, no running jobs"]}
        else:
            for key in ("provider_execution","shared_asset_memory",
                        "targeted_repair","durable_orchestration"):
                steps[key]["status"]="blocked"
                steps[key]["evidence"]=runtime_integrity["failures"]
    except (ValueError, OSError, TypeError, KeyError) as exc:
        for key in ("provider_execution","shared_asset_memory",
                    "targeted_repair","durable_orchestration"):
            steps[key]={"status":"blocked","evidence":[str(exc)]}
    measured=False
    try:
        media=inspect_suite(manifest["media_qc"],root)
        if media["status"]=="checks_passed":
            measured=True
            steps["independent_media_qc"]={"status":"checks_passed",
                "evidence":[x["clip_id"] for x in media["clips"]]}
        else:
            steps["independent_media_qc"]={"status":"blocked",
                "evidence":[f for clip in media["clips"] for f in clip["failures"]]}
    except (ValueError, OSError, TypeError, KeyError, TimeoutError) as exc:
        steps["independent_media_qc"]={"status":"blocked","evidence":[str(exc)]}
    continuity=False
    try:
        story=audit_season_ledger(manifest["season_ledger"])
        if story["status"]=="checks_passed" and story["resolved"]:
            continuity=True
            steps["cross_episode_continuity"]={"status":"checks_passed",
                "evidence":story["resolved"]}
        elif story["status"]=="blocked":
            steps["cross_episode_continuity"]={"status":"blocked",
                "evidence":story["overdue"]}
    except (ValueError, OSError, TypeError, KeyError) as exc:
        steps["cross_episode_continuity"]={"status":"blocked","evidence":[str(exc)]}
    if (runtime_ok and measured and continuity and
        steps["provider_execution"]["status"]=="checks_passed"
        and steps["targeted_repair"]["status"]=="checks_passed"):
        season=manifest["season_benchmark"]
        if season is not None:
            try:
                qualified=audit_season(season,root)
                if (qualified["status"]=="qualified" and qualified["provided_episodes"]>=2):
                    steps["reviewed_multiepisode_delivery"]={
                        "status":"checks_passed",
                        "evidence":[e["number"] for e in qualified["episodes"]]}
                elif qualified["status"]=="blocked":
                    steps["reviewed_multiepisode_delivery"]={
                        "status":"blocked","evidence":["season benchmark blocked"]}
            except (ValueError, OSError, TypeError, KeyError) as exc:
                steps["reviewed_multiepisode_delivery"]={
                    "status":"blocked","evidence":[str(exc)]}
    passes=sum(v["status"]=="checks_passed" for v in steps.values())
    return {"version":1,"status":"fulfilled" if passes==7 else "unfulfilled",
            "passed_stages":passes,"total_stages":7,"stages":steps,
            "limitations":["integrity and basic video signals are measured, not acting fidelity",
                           "provider receipts and human semantic reviews remain attestations",
                           "actual multi-episode media quality must be examined by reviewers"]}
