"""Public semantic interoperability contract: intent -> distinctions -> relations -> outputs.

An institutional, provenance-preserving translation boundary. Its design analogy is the Rosetta Stone: aligned expressions across different
systems anchor to shared meaning. It does not expose private agents or data.
Semantic validity is structural; perceptual correctness needs independent review.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from .collaboration import digest, text, validate_package, PRIVATE_PROJECT_MARKERS

OPS = frozenset({"equivalent", "depends_on", "contradicts", "transforms", "manifests_as"})
STAGES = frozenset({"image", "voice", "video", "editing", "continuity"})
MAX = 500
LAYER_NAMES = frozenset({"semantic", "transport", "execution", "presentation"})

def exact(obj, keys, kind):
    if not isinstance(obj, dict) or set(obj) != set(keys):
        raise ValueError("invalid " + kind + " schema")

def validate_semantics(doc, package):
    validate_package(package)
    exact(doc, ("version", "visibility", "episode_id", "package_sha256", "origin",
                "concepts", "relations", "projections", "review"), "semantic contract")
    if doc["version"] != 1 or doc["visibility"] != "public" or doc["episode_id"] != package["episode_id"]:
        raise ValueError("semantic contract episode or visibility mismatch")
    if doc["package_sha256"] != digest(package):
        raise ValueError("semantic contract has stale collaboration digest")
    if any(m in json.dumps(doc, ensure_ascii=False).casefold() for m in PRIVATE_PROJECT_MARKERS):
        raise ValueError("private context forbidden in public semantic contract")
    origin = doc["origin"]
    exact(origin, ("intent", "source", "scope"), "semantic origin")
    for field in ("intent", "source", "scope"):
        text(origin[field], field)
    concepts = doc["concepts"]
    if not isinstance(concepts, list) or not 1 <= len(concepts) <= MAX:
        raise ValueError("semantic concepts required")
    ids = set()
    for c in concepts:
        exact(c, ("id", "definition", "polarity", "scene_id", "visibility",
                  "evidence", "source_tradition"), "concept")
        cid = text(c["id"], "concept id")
        if cid in ids:
            raise ValueError("duplicate concept")
        ids.add(cid)
        for field in ("definition", "polarity", "evidence", "source_tradition"):
            text(c[field], field)
        if c["visibility"] != "public" or c["scene_id"] not in {s["id"] for s in package["scenes"]}:
            raise ValueError("concept outside authorized scene or visibility")
    relations = doc["relations"]
    if not isinstance(relations, list) or len(relations) > MAX:
        raise ValueError("invalid semantic relations")
    pairs = set()
    for rel in relations:
        exact(rel, ("subject", "operator", "object", "rationale"), "semantic relation")
        if rel["subject"] not in ids or rel["object"] not in ids or rel["subject"] == rel["object"]:
            raise ValueError("semantic relation has invalid endpoints")
        if rel["operator"] not in OPS:
            raise ValueError("unknown semantic operator")
        key = (rel["subject"], rel["object"], rel["operator"])
        if key in pairs:
            raise ValueError("duplicate semantic relation")
        pairs.add(key)
        text(rel["rationale"], "semantic rationale")
    if any((a, b, "equivalent") in pairs and (a, b, "contradicts") in pairs
           for a, b, _ in pairs):
        raise ValueError("direct semantic equivalence and contradiction conflict")
    projections = doc["projections"]
    if not isinstance(projections, list) or not 1 <= len(projections) <= MAX:
        raise ValueError("at least one agent projection required")
    names = set()
    covered = set()
    for p in projections:
        exact(p, ("id", "stage", "scene_id", "concept_ids", "direction",
                  "must_preserve", "must_not_assert", "output_contract"), "projection")
        name = text(p["id"], "projection id")
        if name in names:
            raise ValueError("duplicate projection id")
        names.add(name)
        if p["stage"] not in STAGES or p["scene_id"] not in {s["id"] for s in package["scenes"]}:
            raise ValueError("unknown production stage or scene")
        refs = p["concept_ids"]
        if not isinstance(refs, list) or not refs or len(set(refs)) != len(refs) or any(x not in ids for x in refs):
            raise ValueError("projection has unknown/duplicate concepts")
        if any(next(c["scene_id"] for c in concepts if c["id"] == x) != p["scene_id"] for x in refs):
            raise ValueError("projection crosses scene semantics")
        covered.update(refs)
        for field in ("direction", "output_contract"):
            text(p[field], field)
        for field in ("must_preserve", "must_not_assert"):
            values = p[field]
            if not isinstance(values, list) or not values or len(values) > 40:
                raise ValueError("missing semantic preservation/prohibition rule")
            for v in values:
                text(v, field)
    if covered != ids:
        raise ValueError("unprojected semantic concepts")
    review = doc["review"]
    exact(review, ("approved", "reviewer", "evidence"), "semantic review")
    text(review["reviewer"], "semantic reviewer")
    text(review["evidence"], "semantic evidence")
    if review["approved"] is not True:
        raise ValueError("semantic contract requires human approval")
    return doc

def make_projection(doc, package):
    validate_semantics(doc, package)
    return {"version": 1, "episode_id": doc["episode_id"], "contract_sha256": digest(doc),
            "package_sha256": digest(package), "authorized_projections": doc["projections"],
            "layers": ["semantic", "transport", "execution", "presentation"],
            "scope": "interpretable provider instructions, no vendor-side MCP access asserted"}

def audit_semantics(doc, package, evaluation):
    validate_semantics(doc, package)
    exact(evaluation, ("version", "contract_sha256", "evaluations"), "semantic evaluation")
    if evaluation["version"] != 1 or evaluation["contract_sha256"] != digest(doc):
        raise ValueError("evaluation not bound to canonical semantics")
    items = evaluation["evaluations"]
    if not isinstance(items, list) or len(items) > MAX:
        raise ValueError("invalid semantic evaluation records")
    projections = {p["id"]: p for p in doc["projections"]}
    seen, failures = set(), []
    for item in items:
        exact(item, ("projection_id", "meaning_preserved", "contradiction_found",
                     "prohibitions_respected", "observed_evidence", "reviewer", "approved"),
              "semantic evaluation item")
        pid = text(item["projection_id"], "projection")
        if pid not in projections or pid in seen:
            raise ValueError("duplicate or unknown semantic evaluation")
        seen.add(pid)
        text(item["reviewer"], "reviewer")
        text(item["observed_evidence"], "observed evidence")
        if (item["meaning_preserved"] is not True or
            item["contradiction_found"] is not False or
            item["prohibitions_respected"] is not True or
            item["approved"] is not True):
            failures.append(pid + ":semantic_drift_or_unapproved")
    missing = sorted(set(projections) - seen)
    return {"version": 1, "episode_id": doc["episode_id"],
            "contract_sha256": digest(doc), "package_sha256": digest(package),
            "status": "blocked" if failures else ("incomplete" if missing else "checks_passed"),
            "error_count": len(failures), "unknown_count": len(missing),
            "failures": failures, "unknowns": ["missing_projection:" + pid for pid in missing],
            "scope": "human semantic review and structural proof only; not automatic visual understanding"}
