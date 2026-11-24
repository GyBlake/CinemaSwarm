"""Shot Execution Contract: one shot, shared meaning, explicit production dialects.

Original, provider-neutral contract. Uses ordered source references, approved
character voice IDs, scene blocking, state transitions and semantic/symbolic
references. This does not generate video or prove a vendor followed a prompt.
"""
from __future__ import annotations
import json
from pathlib import Path
from .collaboration import digest, text, validate_package, PRIVATE_PROJECT_MARKERS
from .production_graph import validate_graph
from .semantic_interop import validate_semantics
from .symbolic_narrative import validate_program

MAX_SHOTS = 400
STAGES = ("image", "voice", "video", "editing", "continuity")
REVIEWS = ("identity_preserved", "environment_preserved",
           "dialogue_binding_preserved", "state_transition_preserved",
           "symbolism_preserved", "meaning_preserved", "approved")

def _shape(value, fields, name):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise ValueError("invalid " + name + " schema")

def _names(value, name, allowed=None, *, empty=False):
    if not isinstance(value, list) or len(value)>80 or (not empty and not value):
        raise ValueError("invalid " + name)
    seen = set()
    for item in value:
        text(item, name)
        if item in seen or (allowed is not None and item not in allowed):
            raise ValueError("duplicate or unknown " + name)
        seen.add(item)
    return value

def validate_shots(doc, package, semantic, symbolic, graph):
    validate_package(package)
    validate_semantics(semantic, package)
    validate_program(symbolic, package)
    validate_graph(graph)
    _shape(doc, ("version", "visibility", "episode_id", "package_sha256",
                 "semantic_sha256", "symbolic_sha256", "graph_sha256",
                 "shots", "approved_by", "approved"), "shot execution")
    if doc["version"]!=1 or doc["visibility"]!="public" or doc["episode_id"]!=package["episode_id"] or doc["episode_id"]!=graph["episode_id"]:
        raise ValueError("shot execution identity mismatch")
    for field, source in (("package_sha256",package),("semantic_sha256",semantic),
                          ("symbolic_sha256",symbolic),("graph_sha256",graph)):
        if doc[field]!=digest(source):
            raise ValueError("shot execution stale " + field)
    if any(marker in json.dumps(doc,ensure_ascii=False).casefold() for marker in PRIVATE_PROJECT_MARKERS):
        raise ValueError("private corpus leaked into shot execution")
    text(doc["approved_by"],"shot supervisor")
    if doc["approved"] is not True:
        raise ValueError("shot contract requires human approval")
    shots=doc["shots"]
    if not isinstance(shots,list) or not 1<=len(shots)<=MAX_SHOTS:
        raise ValueError("shot execution requires bounded shot list")
    scenes={s["id"]:s for s in package["scenes"]}
    cast={c["id"]:c for c in package["characters"]}
    lines={d["id"]:d for d in package["dialogue"]}
    beats={b["id"]:b for b in symbolic["beats"]}
    projections={p["id"]:p for p in semantic["projections"]}
    objects={o["id"]:o for o in graph["objects"]}
    shot_ids=set()
    prev_end={}
    for shot in shots:
        _shape(shot, ("id", "scene_id", "start_ms", "end_ms",
                      "cast", "asset_refs", "dialogue_ids", "symbolic_beat_ids",
                      "semantic_projection_ids", "location", "camera",
                      "blocking", "initial_state", "exit_state",
                      "soundscape", "negative_constraints"), "shot")
        sid=text(shot["id"],"shot id")
        if sid in shot_ids:
            raise ValueError("duplicate shot id")
        shot_ids.add(sid)
        scene=scenes.get(shot["scene_id"])
        if scene is None:
            raise ValueError("shot references unknown scene")
        start,end=shot["start_ms"],shot["end_ms"]
        if (type(start) is not int or type(end) is not int or
            not scene["start_ms"]<=start<end<=scene["end_ms"]):
            raise ValueError("shot timing outside scene")
        if start<prev_end.get(shot["scene_id"],scene["start_ms"]):
            raise ValueError("shot order overlaps within scene")
        prev_end[shot["scene_id"]]=end
        _names(shot["cast"],"cast",cast,empty=True)
        refs=shot["asset_refs"]
        if not isinstance(refs,list) or not refs or len(refs)>30:
            raise ValueError("shot requires ordered asset references")
        seen=set()
        for ref in refs:
            _shape(ref,("object_id","sha256"),"shot asset reference")
            rid=ref["object_id"]
            if rid in seen or rid not in objects or ref["sha256"]!=objects[rid]["sha256"]:
                raise ValueError("unknown, duplicate or stale shot reference")
            seen.add(rid)
        for name in ("location","camera","blocking","soundscape"):
            text(shot[name],name)
        for name in ("initial_state","exit_state"):
            state=shot[name]
            _shape(state,("character_positions","prop_state","environment_state"),name)
            for field in ("character_positions","prop_state","environment_state"):
                text(state[field],field)
        _names(shot["negative_constraints"],"negative constraints")
        dialogue_ids=_names(shot["dialogue_ids"],"dialogue",lines,empty=True)
        for lid in dialogue_ids:
            line=lines[lid]
            if line["scene_id"]!=shot["scene_id"] or line["speaker_id"] not in shot["cast"] or line["start_ms"]<start or line["end_ms"]>end:
                raise ValueError("dialogue not scoped to shot or active speaker")
            if line["channel"]=="onscreen" and line["visible_character_id"]!=line["speaker_id"]:
                raise ValueError("visible speaker identity mismatch")
        for cid in shot["cast"]:
            bound=cast[cid]
            if not bound["voice_approved"]:
                raise ValueError("cast voice not approved")
        beat_ids=_names(shot["symbolic_beat_ids"],"symbolic beats",beats,empty=True)
        for bid in beat_ids:
            b=beats[bid]
            if b["scene_id"]!=shot["scene_id"] or b["start_ms"]<start or b["end_ms"]>end:
                raise ValueError("symbolic event not contained within shot")
        proj_ids=_names(shot["semantic_projection_ids"],"semantic projections",projections)
        for pid in proj_ids:
            p=projections[pid]
            if p["scene_id"]!=shot["scene_id"]:
                raise ValueError("semantic projection crosses scene boundary")
        if (not any(projections[p]["stage"]=="video" for p in proj_ids)
            and not any(projections[p]["stage"]=="image" for p in proj_ids)):
            raise ValueError("shot needs image or video semantic projection")
    covered_lines={x for shot in shots for x in shot["dialogue_ids"]}
    if covered_lines!={line["id"] for line in package["dialogue"]}:
        raise ValueError("shot contract must map all dialogue without dropping lines")
    covered_beats={x for shot in shots for x in shot["symbolic_beat_ids"]}
    if covered_beats!={b["id"] for b in symbolic["beats"]}:
        raise ValueError("shot contract must map all symbolic beats")
    return doc

def stage_handoffs(doc, package, semantic, symbolic, graph):
    validate_shots(doc,package,semantic,symbolic,graph)
    projections={p["id"]:p for p in semantic["projections"]}
    lines={d["id"]:d for d in package["dialogue"]}
    cast={c["id"]:c for c in package["characters"]}
    beats={b["id"]:b for b in symbolic["beats"]}
    out=[]
    for shot in doc["shots"]:
        stage_map={}
        for stage in STAGES:
            matching=[projections[k] for k in shot["semantic_projection_ids"]
                      if projections[k]["stage"]==stage]
            if not matching and stage not in ("video","image"):
                continue
            if matching:
                stage_map[stage]={
                    "meaning_ids":list(dict.fromkeys(x for p in matching for x in p["concept_ids"])),
                    "directions":[p["direction"] for p in matching],
                    "must_preserve":[v for p in matching for v in p["must_preserve"]],
                    "must_not_assert":[v for p in matching for v in p["must_not_assert"]]}
        dialogue=[{"id":lid,"speaker":lines[lid]["speaker_id"],
                   "channel":lines[lid]["channel"],
                   "voice_id":cast[lines[lid]["speaker_id"]]["voice_id"],
                   "text":lines[lid]["text"]} for lid in shot["dialogue_ids"]]
        out.append({"shot_id":shot["id"],"scene_id":shot["scene_id"],
                    "start_ms":shot["start_ms"],"end_ms":shot["end_ms"],
                    "ordered_asset_refs":shot["asset_refs"],"cast":shot["cast"],
                    "camera":shot["camera"],"blocking":shot["blocking"],
                    "location":shot["location"],"initial_state":shot["initial_state"],
                    "exit_state":shot["exit_state"],"soundscape":shot["soundscape"],
                    "negative_constraints":shot["negative_constraints"],
                    "dialogue":dialogue,
                    "symbolic_directions":[{"id":bid,"channel":beats[bid]["channel"],
                        "direction":beats[bid]["perceptual_directive"],
                        "reveal_policy":beats[bid]["reveal_policy"]}
                        for bid in shot["symbolic_beat_ids"]],
                    "stage_semantics":stage_map})
    return {"version":1,"episode_id":doc["episode_id"],
            "shot_contract_sha256":digest(doc),"package_sha256":digest(package),
            "semantic_sha256":digest(semantic),"symbolic_sha256":digest(symbolic),
            "graph_sha256":digest(graph),"shots":out,
            "scope":"provider-neutral authorized handoffs; actual provider execution not claimed"}

def audit_shot_evidence(doc, package, semantic, symbolic, graph, report):
    validate_shots(doc,package,semantic,symbolic,graph)
    _shape(report,("version","contract_sha256","reviews"),"shot evidence")
    if report["version"]!=1 or report["contract_sha256"]!=digest(doc):
        raise ValueError("shot evidence not bound to approved contract")
    records=report["reviews"]
    if not isinstance(records,list) or len(records)>MAX_SHOTS:
        raise ValueError("invalid shot review records")
    shots={s["id"] for s in doc["shots"]}
    seen=set()
    failures=[]
    for item in records:
        _shape(item,("shot_id","evidence_sha256","reviewer","evidence",
                     *REVIEWS),"shot review")
        sid=text(item["shot_id"],"review shot")
        if sid not in shots or sid in seen:
            raise ValueError("unknown or duplicate shot review")
        seen.add(sid)
        sha=item["evidence_sha256"]
        if not isinstance(sha,str) or len(sha)!=64 or any(x not in "0123456789abcdef" for x in sha):
            raise ValueError("invalid shot review evidence digest")
        text(item["reviewer"],"reviewer")
        text(item["evidence"],"evidence")
        for field in REVIEWS:
            if item[field] is not True:
                failures.append(f"{sid}:{field}")
    missing=sorted(shots-seen)
    return {"version":1,"episode_id":doc["episode_id"],
            "package_sha256":digest(package),"contract_sha256":digest(doc),
            "status":"blocked" if failures else ("incomplete" if missing else "checks_passed"),
            "error_count":len(failures),"unknown_count":len(missing),
            "failures":failures,"unknowns":missing,
            "scope":"reviewer-attested evidence; does not independently inspect video pixels, lip movement, or provider cognition"}
