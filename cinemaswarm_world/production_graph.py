"""CinemaSwarm production provenance, ordered references, and take approval.

Original adapter inspired by general production-control concepts, not a clone of
any external repository's code or protocol. Every applied output is traceable
to its exact input hashes. A declared provider receipt is not independently
verified evidence of a model's internal behavior.
"""
from __future__ import annotations
from pathlib import Path
import hashlib
from .collaboration import text, load_json, digest, PRIVATE_PROJECT_MARKERS

KINDS = ("screenplay", "bible", "character", "location", "prop", "scene",
         "storyboard", "keyframe", "dialogue_audio", "take", "cut", "subtitles")
MAX_OBJECTS = 500
MAX_OUTPUT_BYTES = 250_000_000
REQUIRED_STOPS = ("assets_planned", "assets_approved",
                  "shots_planned", "storyboard_approved", "takes_reviewed")

def sha(value):
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError("invalid SHA-256")
    return value

def path_in(root, relative):
    name = Path(text(relative, "production path"))
    if name.is_absolute():
        raise ValueError("absolute production path forbidden")
    base = Path(root).resolve(strict=True)
    path = (base / name).resolve(strict=True)
    if not path.is_relative_to(base) or not path.is_file() or path.stat().st_size > MAX_OUTPUT_BYTES:
        raise ValueError("production file missing, oversized or escapes root")
    return path

def file_sha(path):
    h = hashlib.sha256()
    with path.open("rb") as fd:
        for part in iter(lambda: fd.read(1_048_576), b""):
            h.update(part)
    return h.hexdigest()

def validate_graph(doc):
    if not isinstance(doc, dict) or set(doc) != {"version", "episode_id", "visibility", "objects", "stops", "cut"} or doc["version"] != 1 or doc["visibility"] != "public":
        raise ValueError("invalid public production graph")
    text(doc["episode_id"], "episode")
    from json import dumps
    if any(marker in dumps(doc, ensure_ascii=False).casefold() for marker in PRIVATE_PROJECT_MARKERS):
        raise ValueError("private context forbidden in public production graph")
    objects = doc["objects"]
    if not isinstance(objects, list) or not 1 <= len(objects) <= MAX_OBJECTS:
        raise ValueError("production objects required")
    known = {}
    for obj in objects:
        if not isinstance(obj, dict) or set(obj) != {"id", "kind", "source", "sha256",
                                                     "inputs_sent_in_order", "receipt"}:
            raise ValueError("invalid production object")
        oid = text(obj["id"], "object id")
        if oid in known:
            raise ValueError("duplicate production object")
        if obj["kind"] not in KINDS:
            raise ValueError("unrecognized production object kind")
        text(obj["source"], "object source")
        sha(obj["sha256"])
        refs = obj["inputs_sent_in_order"]
        if not isinstance(refs, list) or len(refs) > 30:
            raise ValueError("invalid ordered input references")
        seen_refs = set()
        for ref in refs:
            if not isinstance(ref, dict) or set(ref) != {"id", "sha256"}:
                raise ValueError("invalid input reference")
            rid = text(ref["id"], "referenced object")
            sha(ref["sha256"])
            if rid not in known or rid in seen_refs or known[rid]["sha256"] != ref["sha256"]:
                raise ValueError("stale, duplicate, missing, or forward input reference")
            seen_refs.add(rid)
        receipt = obj["receipt"]
        if receipt is not None:
            if not isinstance(receipt, dict) or set(receipt) != {"provider", "request_id", "output_sha256",
                                                                "input_sha256s_in_order", "cost_usd",
                                                                "cost_approved", "reviewer"}:
                raise ValueError("invalid provider production receipt")
            text(receipt["provider"], "provider")
            text(receipt["request_id"], "request id")
            text(receipt["reviewer"], "cost approval reviewer")
            if receipt["output_sha256"] != obj["sha256"]:
                raise ValueError("receipt output does not match production object")
            if receipt["input_sha256s_in_order"] != [r["sha256"] for r in refs]:
                raise ValueError("receipt inputs differ from actual ordered references")
            cost = receipt["cost_usd"]
            if cost is not None and (type(cost) not in (int, float) or not 0 <= cost <= 100000):
                raise ValueError("invalid reported cost")
            if receipt["cost_approved"] is not True:
                raise ValueError("paid production needs cost approval")
        known[oid] = obj
    stops = doc["stops"]
    if not isinstance(stops, dict) or set(stops) != set(REQUIRED_STOPS):
        raise ValueError("mandatory production approval stops missing")
    for stop in REQUIRED_STOPS:
        review = stops[stop]
        if not isinstance(review, dict) or set(review) != {"approved", "reviewer", "evidence"}:
            raise ValueError("invalid production stop")
        text(review["reviewer"], "production reviewer")
        text(review["evidence"], "approval evidence")
        if review["approved"] is not True:
            raise ValueError("production stop not approved: " + stop)
    cut = doc["cut"]
    if not isinstance(cut, dict) or set(cut) != {"object_id", "take_ids"}:
        raise ValueError("invalid final cut")
    if cut["object_id"] not in known or known[cut["object_id"]]["kind"] != "cut":
        raise ValueError("final cut object missing")
    takes = cut["take_ids"]
    if not isinstance(takes, list) or not takes or len(takes) > 120 or len(set(takes)) != len(takes):
        raise ValueError("final cut must select distinct takes")
    for take_id in takes:
        if take_id not in known or known[take_id]["kind"] != "take":
            raise ValueError("final cut references invalid take")
        if take_id not in [r["id"] for r in known[cut["object_id"]]["inputs_sent_in_order"]]:
            raise ValueError("final cut missing explicit take input")
    return doc

def audit_graph(doc, root):
    validate_graph(doc)
    failures = []
    details = []
    for obj in doc["objects"]:
        try:
            actual = file_sha(path_in(root, obj["source"]))
            if actual != obj["sha256"]:
                failures.append(obj["id"] + ":hash_mismatch")
        except (OSError, ValueError):
            failures.append(obj["id"] + ":file_unavailable")
        details.append({"id": obj["id"], "kind": obj["kind"], "input_ids":
                        [r["id"] for r in obj["inputs_sent_in_order"]],
                        "has_provider_receipt": obj["receipt"] is not None})
    return {"version": 1, "episode_id": doc["episode_id"],
            "graph_sha256": digest(doc),
            "status": "blocked" if failures else "checks_passed",
            "error_count": len(failures), "unknown_count": 0,
            "failures": failures, "objects": details,
            "scope": "file hashes, explicit dependencies, provider receipt metadata and attributed human approvals; not independent verification of provider cognition"}
