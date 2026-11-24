"""Production runtime for approved, immutable assets, authorized jobs and provider receipts.

This is provider-neutral: remote models are invoked by an explicitly configured
adapter outside this module. No SDK availability, paid call, or video generation
is inferred by accepting a job or a receipt. Persistent state is on local disk.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import tempfile
from datetime import datetime, timezone
from .collaboration import digest, text, PRIVATE_PROJECT_MARKERS

KIND = frozenset({"image", "voice", "video", "lipsync", "edit", "analyze", "repair"})
STATES = frozenset({"planned", "authorized", "running", "imported", "verified",
                    "rejected", "failed"})
MAX_BYTES = 500_000_000
MAX_JOBS = 1000
MAX_ASSETS = 1000

def _schema(obj, fields, label):
    if not isinstance(obj, dict) or set(obj) != set(fields):
        raise ValueError("invalid " + label)

def _id(v, label):
    text(v, label)
    if len(v) > 96 or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-." for c in v):
        raise ValueError("unsafe " + label)
    return v

def _sha(value):
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError("invalid SHA-256")
    return value

def _path(root, relative):
    if not isinstance(relative, str) or not relative or len(relative) > 512:
        raise ValueError("bad path")
    name = Path(relative)
    if name.is_absolute() or ".." in name.parts:
        raise ValueError("path outside approved root")
    base = Path(root).resolve(strict=True)
    resolved = (base / name).resolve(strict=True)
    if not resolved.is_file() or not resolved.is_relative_to(base) or resolved.stat().st_size > MAX_BYTES:
        raise ValueError("unsafe or oversized production asset")
    return resolved

def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for blob in iter(lambda: stream.read(1_048_576), b""):
            h.update(blob)
    return h.hexdigest()

def validate_runtime(doc):
    _schema(doc, ("version", "episode_id", "visibility", "budget_limit_usd",
                  "assets", "jobs", "checkpoints"), "runtime")
    if doc["version"] != 1 or doc["visibility"] != "public":
        raise ValueError("runtime must be version 1 and public")
    _id(doc["episode_id"], "episode_id")
    if any(marker in json.dumps(doc, ensure_ascii=False).casefold() for marker in PRIVATE_PROJECT_MARKERS):
        raise ValueError("private project marker in public runtime")
    budget = doc["budget_limit_usd"]
    if type(budget) not in (float, int) or not 0 <= budget <= 100000:
        raise ValueError("invalid budget")
    assets = doc["assets"]
    if not isinstance(assets, list) or len(assets) > MAX_ASSETS:
        raise ValueError("invalid asset registry")
    asset_ids = {}
    for a in assets:
        _schema(a, ("id", "kind", "path", "sha256", "approved", "reviewer",
                    "canonical_ref", "origin_job"), "asset")
        aid = _id(a["id"], "asset id")
        if aid in asset_ids:
            raise ValueError("duplicate asset")
        if a["kind"] not in KIND or a["approved"] is not True:
            raise ValueError("asset missing review approval")
        _sha(a["sha256"])
        text(a["path"], "asset path")
        text(a["reviewer"], "asset reviewer")
        _id(a["canonical_ref"], "canon reference")
        if a["origin_job"] is not None:
            _id(a["origin_job"], "origin job")
        asset_ids[aid] = a
    jobs = doc["jobs"]
    if not isinstance(jobs, list) or len(jobs) > MAX_JOBS:
        raise ValueError("invalid job registry")
    known, total = {}, 0
    for job in jobs:
        _schema(job, ("id", "kind", "provider", "inputs", "dependencies",
                      "contract_sha256", "estimated_cost_usd", "actual_cost_usd",
                      "state", "authorized_by", "idempotency_key", "output_asset",
                      "attempt", "parent_job", "provider_receipt"), "job")
        jid = _id(job["id"], "job id")
        if jid in known:
            raise ValueError("duplicate job id")
        if job["kind"] not in KIND or job["state"] not in STATES:
            raise ValueError("invalid job kind or state")
        text(job["provider"], "provider")
        _sha(job["contract_sha256"])
        estimate = job["estimated_cost_usd"]
        actual = job["actual_cost_usd"]
        if type(estimate) not in (int, float) or not 0 <= estimate <= 100000:
            raise ValueError("invalid cost estimate")
        if actual is not None and (type(actual) not in (int, float) or not 0 <= actual <= 100000):
            raise ValueError("invalid actual cost")
        total += actual if actual is not None else estimate
        if total > budget:
            raise ValueError("job portfolio exceeds approved budget")
        if not isinstance(job["inputs"], list) or len(job["inputs"]) > 50:
            raise ValueError("invalid ordered inputs")
        inputs = []
        for inp in job["inputs"]:
            _schema(inp, ("asset_id", "sha256"), "job input")
            if inp["asset_id"] not in asset_ids or asset_ids[inp["asset_id"]]["sha256"] != inp["sha256"]:
                raise ValueError("job input missing or stale")
            inputs.append((inp["asset_id"], inp["sha256"]))
        if len(inputs) != len(set(inputs)):
            raise ValueError("duplicate job input")
        depends = job["dependencies"]
        if not isinstance(depends, list) or len(depends) != len(set(depends)) or any(dep not in known for dep in depends):
            raise ValueError("unknown, duplicate or forward job dependency")
        if job["state"] != "planned":
            text(job["authorized_by"], "authorizing reviewer")
        if job["state"] in ("running", "imported", "verified") and any(known[dep]["state"] != "verified" for dep in depends):
            raise ValueError("job started before dependencies verified")
        _sha(job["idempotency_key"])
        expected_key = digest({"episode_id": doc["episode_id"], "kind": job["kind"],
                               "provider": job["provider"], "inputs": job["inputs"],
                               "contract_sha256": job["contract_sha256"],
                               "parent_job": job["parent_job"], "attempt": job["attempt"]})
        if job["idempotency_key"] != expected_key:
            raise ValueError("invalid idempotency key")
        if type(job["attempt"]) is not int or not 1 <= job["attempt"] <= 5:
            raise ValueError("invalid attempt")
        if job["parent_job"] is not None and job["parent_job"] not in known:
            raise ValueError("repair parent missing")
        if job["output_asset"] is not None:
            if job["output_asset"] not in asset_ids:
                raise ValueError("output asset absent from registry")
            if asset_ids[job["output_asset"]]["origin_job"] != jid:
                raise ValueError("output asset origin mismatch")
        if job["state"] in ("imported", "verified") and job["output_asset"] is None:
            raise ValueError("completed job without output asset")
        receipt = job["provider_receipt"]
        if receipt is not None:
            _schema(receipt, ("provider_request_id", "input_sha256s", "output_sha256",
                              "cost_usd", "evidence"), "provider receipt")
            text(receipt["provider_request_id"], "request")
            text(receipt["evidence"], "provider evidence")
            if receipt["input_sha256s"] != [i["sha256"] for i in job["inputs"]]:
                raise ValueError("provider input receipt mismatch")
            _sha(receipt["output_sha256"])
            if job["output_asset"] is None or receipt["output_sha256"] != asset_ids[job["output_asset"]]["sha256"]:
                raise ValueError("provider output receipt mismatch")
            if receipt["cost_usd"] != job["actual_cost_usd"]:
                raise ValueError("provider receipt cost mismatch")
        if job["state"] in ("imported", "verified") and receipt is None:
            raise ValueError("completed provider job missing receipt")
        if job["state"] == "verified" and asset_ids[job["output_asset"]]["approved"] is not True:
            raise ValueError("unapproved verified output")
        known[jid] = job
    if len({j["idempotency_key"] for j in jobs}) != len(jobs):
        raise ValueError("duplicate idempotent execution")
    for asset in assets:
        if asset["origin_job"] is not None and asset["origin_job"] not in known:
            raise ValueError("orphan generated asset")
    stops = doc["checkpoints"]
    if not isinstance(stops, list) or len(stops) > 500:
        raise ValueError("invalid checkpoints")
    names = set()
    for item in stops:
        _schema(item, ("name", "state_digest", "reviewer", "approved"), "checkpoint")
        name = _id(item["name"], "checkpoint")
        if name in names:
            raise ValueError("duplicate checkpoint")
        names.add(name)
        _sha(item["state_digest"])
        text(item["reviewer"], "checkpoint reviewer")
        if item["approved"] is not True:
            raise ValueError("unapproved checkpoint")
    return doc

def audit_runtime(doc, root):
    validate_runtime(doc)
    failures = []
    details = []
    for asset in doc["assets"]:
        try:
            h = file_sha(_path(root, asset["path"]))
            if h != asset["sha256"]:
                failures.append(asset["id"] + ":hash_mismatch")
        except (OSError, ValueError):
            failures.append(asset["id"] + ":unavailable")
        details.append({"asset_id": asset["id"], "sha256": asset["sha256"]})
    return {"version": 1, "episode_id": doc["episode_id"],
            "runtime_sha256": digest(doc), "status": "blocked" if failures else "checks_passed",
            "error_count": len(failures), "unknown_count": 0, "failures": failures,
            "assets": details, "jobs": [{"id": j["id"], "state": j["state"]}
                                        for j in doc["jobs"]],
            "scope": "integrity and provider receipt reconciliation; no model invocation"}

def make_job(episode_id, job_id, kind, provider, inputs, contract_sha256,
             cost_estimate, authorized_by, dependencies=None, parent_job=None,
             attempt=1):
    job = {"id": job_id, "kind": kind, "provider": provider, "inputs": inputs,
           "dependencies": dependencies or [], "contract_sha256": contract_sha256,
           "estimated_cost_usd": cost_estimate, "actual_cost_usd": None,
           "state": "authorized", "authorized_by": authorized_by,
           "output_asset": None, "attempt": attempt, "parent_job": parent_job,
           "provider_receipt": None}
    job["idempotency_key"] = digest({
        "episode_id": episode_id, "kind": kind, "provider": provider, "inputs": inputs,
        "contract_sha256": contract_sha256, "parent_job": parent_job, "attempt": attempt})
    return job

def plan_repair(doc, failed_job_id, replacement_id, authorized_by, changed_inputs=None):
    validate_runtime(doc)
    failed = next((j for j in doc["jobs"] if j["id"] == failed_job_id), None)
    if failed is None or failed["state"] not in ("rejected", "failed"):
        raise ValueError("repair requires explicitly failed or rejected job")
    repaired = make_job(doc["episode_id"], replacement_id, failed["kind"],
                        failed["provider"], changed_inputs if changed_inputs is not None else failed["inputs"],
                        failed["contract_sha256"], failed["estimated_cost_usd"],
                        authorized_by, failed["dependencies"], failed["id"],
                        failed["attempt"] + 1)
    candidate = json.loads(json.dumps(doc))
    candidate["jobs"].append(repaired)
    validate_runtime(candidate)
    return candidate

def write_atomic(path, doc, overwrite=False):
    path = Path(path)
    if path.exists() and not overwrite:
        raise ValueError("output exists; explicit overwrite required")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, tmp = tempfile.mkstemp(prefix=".cinemaswarm-", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2, ensure_ascii=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
