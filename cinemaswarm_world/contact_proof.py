"""Previsualization continuity validator for Nia/Vesper's contact proof.

This validates planning data; it never claims generated or reviewed footage.
"""
from __future__ import annotations
import json
from pathlib import Path
from .pilot_scene_roles import validate_scene_roles

def _exact(value,keys,label):
    if not isinstance(value,dict) or set(value)!=set(keys):
        raise ValueError("invalid "+label)

def _string(value,label):
    if not isinstance(value,str) or not value.strip() or len(value)>700:
        raise ValueError("invalid "+label)

def validate_contact(identity,sequence,scene_roles,roles,season):
    validate_scene_roles(scene_roles,roles,season)
    _exact(identity,("version","season_id","episode_id","status","subjects","relationship","review"),"identity")
    _exact(sequence,("version","season_id","episode_id","sequence_id","status","target_seconds","shot_ids","shots","production","review"),"sequence")
    for doc in (identity,sequence):
        if doc["version"]!=1 or doc["season_id"]!=season["season_id"] or doc["episode_id"]!="e01-totality":
            raise ValueError("identity episode continuity")
    if identity["status"]!="design_draft" or sequence["status"]!="previsualization_draft":
        raise ValueError("unsupported readiness state")
    subjects=identity["subjects"]
    if not isinstance(subjects,list) or [s.get("id") for s in subjects]!=["nia","vesper"]:
        raise ValueError("Nexus host or voice changed")
    for sub in subjects:
        _exact(sub,("id","name","kind","role","design","voice","approval"),"identity subject")
        if sub["approval"] is not False:
            raise ValueError("unreviewed identity marked approved")
        _exact(sub["voice"],("accent","range","pace","performance","speech_rules"),"voice")
        for key in ("accent","range","pace","performance"):
            _string(sub["voice"][key],key)
        if not isinstance(sub["voice"]["speech_rules"],list) or not sub["voice"]["speech_rules"]:
            raise ValueError("speech limits missing")
        design=sub["design"]
        if not isinstance(design,dict) or not design.get("forbidden_changes"):
            raise ValueError("character consistency limits missing")
        if not isinstance(design["forbidden_changes"],list):
            raise ValueError("character consistency limits invalid")
    if subjects[0]["kind"]!="human" or subjects[1]["kind"]!="subjective_companion":
        raise ValueError("subject types mismatch")
    rel=identity["relationship"]
    _exact(rel,("host_id","companion_id","mode","nexus_class","subjective_rendering",
                "ordinary_reverse_visible","independent_physical_presence"),"host relation")
    if (rel["host_id"]!="nia" or rel["companion_id"]!="vesper" or rel["mode"]!="waking_dream"
        or rel["nexus_class"] is not True or rel["subjective_rendering"] is not True
        or rel["ordinary_reverse_visible"] is not False
        or rel["independent_physical_presence"] is not False):
        raise ValueError("private Nexus visibility invariant")
    ids=sequence["shot_ids"]
    if ids!=["S03","S04","S10","S11"] or len(sequence["shots"])!=4:
        raise ValueError("wrong proof shot sequence")
    permitted={"S03":"e01-sc02","S04":"e01-sc02","S10":"e01-sc06","S11":"e01-sc06"}
    total=0
    for item,shot_id in zip(sequence["shots"],ids):
        _exact(item,("id","scene_id","seconds","view","camera","action","audio",
                     "dialogue","effects","continuity"),"proof shot")
        if item["id"]!=shot_id or item["scene_id"]!=permitted[shot_id]:
            raise ValueError("cross-scene shot continuity")
        if type(item["seconds"]) is not int or not 4<=item["seconds"]<=20:
            raise ValueError("invalid proof shot duration")
        total+=item["seconds"]
        expected_view="subjective" if shot_id=="S10" else "objective"
        if item["view"]!=expected_view:
            raise ValueError("objective and subjective image leak")
        for field in ("camera","action","audio","effects","continuity"):
            _string(item[field],field)
        dialogue=item["dialogue"]
        if not isinstance(dialogue,list):
            raise ValueError("invalid proof dialogue")
        for line in dialogue:
            _exact(line,("speaker","line"),"spoken line")
            if line["speaker"] not in ("nia","vesper"):
                raise ValueError("unauthorized proof speaker")
            _string(line["line"],"spoken line")
            if line["speaker"]=="vesper" and item["view"]!="subjective":
                raise ValueError("Vesper voice audible in neutral camera")
    if total!=40 or sequence["target_seconds"]!=40:
        raise ValueError("proof duration mismatch")
    production=sequence["production"]
    _exact(production,("aspect_ratio","resolution_target","fps_target","audio_target",
                       "output_kind","source_assets_produced","dialogue_recorded",
                       "performance_approved","rendered_video","paid_generation_authorized","stage"),
           "production state")
    if (production["stage"]!="planning_only" or production["output_kind"]!="cinematic proof-of-concept"
        or production["aspect_ratio"]!="16:9" or production["resolution_target"]!="1920x1080"
        or production["fps_target"]!=24 or production["audio_target"]!="48kHz stereo"
        or any(production[k] is not False for k in (
            "source_assets_produced","dialogue_recorded","performance_approved",
            "rendered_video","paid_generation_authorized"))):
        raise ValueError("unverified proof-of-concept completion")
    review=sequence["review"]
    _exact(review,("shot_plan_approved","asset_approval","dialogue_approval","evidence"),"review")
    if any(review[k] is not False for k in ("shot_plan_approved","asset_approval","dialogue_approval")):
        raise ValueError("unapproved proof-of-concept")
    _string(review["evidence"],"review evidence")
    i_review=identity["review"]
    _exact(i_review,("art_direction_approved","voice_approved","likeness_approved",
                      "performance_approved","evidence"),"identity review")
    if any(i_review[k] is not False for k in (
         "art_direction_approved","voice_approved","likeness_approved","performance_approved")):
        raise ValueError("unreviewed identity approved")
    _string(i_review["evidence"],"identity evidence")
    return sequence

def load_contact(identity_path,sequence_path,scene_roles,roles,season):
    a=json.loads(Path(identity_path).read_text(encoding="utf-8"))
    b=json.loads(Path(sequence_path).read_text(encoding="utf-8"))
    return validate_contact(a,b,scene_roles,roles,season)
