"""Episode scene dramatic function and role-continuity validator.

Development planning only, not physical scene/media verification.
"""
from __future__ import annotations
import json
from pathlib import Path
from .character_roles import validate_character_roles

ACTS = frozenset({"prologue","setup","threshold","aftermath","test","opposition_seed","hook"})
FIELDS = frozenset({"number","scene_id","act","focus","participants","functions",
                    "conflict","decision","reveal","continuity","shots","reviewed"})
SHOTS = {"S"+str(i).zfill(2) for i in range(1,16)}

def validate_scene_roles(doc,role_doc,season):
    validate_character_roles(role_doc,season)
    if not isinstance(doc,dict) or set(doc) != {
        "version","season_id","episode_id","status","declared_shots","scenes","requirements"
    }:
        raise ValueError("invalid pilot scene contract")
    if (doc["version"]!=1 or doc["season_id"]!=season["season_id"]
            or doc["episode_id"]!=season["episodes"][0]["id"]
            or doc["status"]!="scene_development_draft" or doc["declared_shots"]!=15):
        raise ValueError("pilot scene metadata mismatch")
    entities={x["id"]:set(x["roles"]) for x in role_doc["characters"]}
    scenes=doc["scenes"]
    if not isinstance(scenes,list) or len(scenes)!=10:
        raise ValueError("pilot must map all ten script scenes")
    shots=[]
    focus_seen=set()
    for index,scene in enumerate(scenes,1):
        if not isinstance(scene,dict) or set(scene)!=FIELDS:
            raise ValueError("invalid scene entry")
        if scene["number"]!=index or scene["scene_id"]!=f"e01-sc{index:02d}":
            raise ValueError("pilot scene ordering")
        if scene["act"] not in ACTS or scene["reviewed"] is not False:
            raise ValueError("scene incorrectly approved or unclassified")
        if not isinstance(scene["participants"],list) or len(set(scene["participants"]))!=len(scene["participants"]):
            raise ValueError("duplicate scene participants")
        if not set(scene["participants"]) <= entities:
            raise ValueError("scene participant not in cast registry")
        if scene["focus"]!="historical_record":
            if scene["focus"] not in scene["participants"]:
                raise ValueError("scene focus missing from participants")
            focus_seen.add(scene["focus"])
        elif index!=1 or scene["participants"]:
            raise ValueError("unassigned viewpoint outside archival prologue")
        functions=scene["functions"]
        if not isinstance(functions,list) or not functions or len(set(functions))!=len(functions):
            raise ValueError("missing dramatic roles")
        known={r["id"] for r in role_doc["taxonomy"]}
        if not set(functions)<=known:
            raise ValueError("scene uses unknown dramatic function")
        if scene["focus"]!="historical_record" and not (set(functions) & entities[scene["focus"]]):
            raise ValueError("scene role inconsistent with viewpoint")
        for k in ("conflict","decision","reveal","continuity"):
            if not isinstance(scene[k],str) or not scene[k].strip() or len(scene[k])>600:
                raise ValueError("empty scene purpose or invalid continuity")
        if not isinstance(scene["shots"],list) or not scene["shots"] or not set(scene["shots"])<=SHOTS:
            raise ValueError("unknown pilot shot")
        shots += scene["shots"]
        if index in (2,6,8,10) and "nia" not in scene["participants"]:
            raise ValueError("Nexus scene missing protagonist")
        if index==6 and "vesper" not in scene["participants"]:
            raise ValueError("Nexus origin lacks canonical companion")
    if set(shots)!=SHOTS or len(shots)!=15:
        raise ValueError("missing or duplicated pilot shot")
    if not {"nia","mateo","mara","elias","leena"} <= focus_seen:
        raise ValueError("ensemble perspective absent")
    req=doc["requirements"]
    if not isinstance(req,dict) or set(req)!={"role_registry","season_handoff",
                                               "screenplay","approval","render_ready"}:
        raise ValueError("scene handoff missing evidence")
    if req["approval"] is not False or req["render_ready"] is not False:
        raise ValueError("unreviewed scenes may not be released")
    if (req["role_registry"]!="docs/season-01/character-roles.json"
            or req["season_handoff"]!="docs/season-01/season-handoff.json"
            or req["screenplay"]!="docs/season-01/e01-totality-script.md"):
        raise ValueError("scene references wrong canon files")
    return doc

def observe_scene_roles(doc,role_doc,season):
    validate_scene_roles(doc,role_doc,season)
    return {"episode_id":doc["episode_id"],"scene_count":len(doc["scenes"]),
            "shot_count":len(SHOTS),"approved":False,
            "scenes":[{"id":s["scene_id"],"focus":s["focus"],"roles":s["functions"],
                       "decision":s["decision"],"reveal":s["reveal"],
                       "shot_ids":s["shots"]} for s in doc["scenes"]]}

def load_scene_roles(path,role_doc,season):
    with Path(path).open(encoding="utf-8") as f:
        return validate_scene_roles(json.load(f),role_doc,season)
