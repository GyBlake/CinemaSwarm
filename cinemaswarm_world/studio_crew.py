"""CinemaSwarm studio crew bus: bounded, read-only handoffs and gated job topology.

This is a working deterministic pre-production orchestrator, not an AI video
provider or a substitute for live actor, gaffer, stagehand or editor operations.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from .collaboration import PRIVATE_PROJECT_MARKERS, digest
from .camera_engineer import validate_camera_engineer
from .studio_runtime import validate_runtime

PHASES = ("preproduction", "production", "postproduction", "release")
CREW = (
    "executive_producer", "showrunner", "director", "continuity_warden",
    "stage_manager", "thespian_director", "cinematographer", "camera_engineer",
    "camera_operator", "first_ac", "art_department", "gaffer",
    "sound_department", "vfx_supervisor", "editor", "quality_control",
    "publishing", "archive",
)
# All producer-paid or performed stages stay blocked until explicit approval.
PLANNING = ("showrunner", "director", "continuity_warden", "stage_manager",
            "thespian_director", "cinematographer", "camera_engineer", "art_department")
DEPENDENCIES = {
    "showrunner": (),
    "director": ("showrunner",),
    "continuity_warden": ("showrunner",),
    "stage_manager": ("director","continuity_warden"),
    "thespian_director": ("director",),
    "cinematographer": ("director",),
    "camera_engineer": ("cinematographer","stage_manager"),
    "art_department": ("stage_manager",),
    "camera_operator": ("camera_engineer","art_department"),
    "first_ac": ("camera_engineer",),
    "gaffer": ("cinematographer","art_department"),
    "sound_department": ("thespian_director",),
    "vfx_supervisor": ("camera_operator","sound_department"),
    "editor": ("vfx_supervisor","first_ac","gaffer"),
    "quality_control": ("editor",),
    "publishing": ("quality_control",),
    "archive": ("publishing",),
}
FORBIDDEN = {"running", "verified", "finished", "released"}

def _shape(x, fields, label):
    if not isinstance(x, dict) or set(x) != set(fields):
        raise ValueError("invalid " + label)

def validate_crew_registry(doc, season, identity, contact, scenes, roles, camera):
    _shape(doc, ("version","visibility","season_id","episode_id","sequence_id",
                 "status","registry","shared_state","policy"), "crew registry")
    if (doc["version"]!=1 or doc["visibility"]!="public"
        or doc["season_id"]!=season["season_id"]
        or doc["episode_id"]!=contact["episode_id"]
        or doc["sequence_id"]!=contact["sequence_id"]
        or doc["status"]!="preproduction_only"):
        raise ValueError("crew registry episode mismatch")
    serialized=json.dumps(doc,ensure_ascii=False).casefold()
    if any(marker in serialized for marker in PRIVATE_PROJECT_MARKERS):
        raise ValueError("private crew leakage")
    members=doc["registry"]
    if not isinstance(members,list) or [x.get("id") for x in members]!=list(CREW):
        raise ValueError("incomplete or duplicate crew registry")
    for m in members:
        _shape(m,("id","phase","mission","input","output","approval_gate"),"crew member")
        if (m["phase"] not in ("executive",)+PHASES or any(
            not isinstance(m[key],str) or not m[key].strip()
            for key in ("mission","input","output","approval_gate"))):
            raise ValueError("crew role capability missing")
    state=doc["shared_state"]
    _shape(state,("stage","scene_ids","camera_plan_ref","contact_ref",
                  "character_ref","cast","anchors","props","approval","revision"),
           "shared scene state")
    if (state["stage"]!="design" or state["scene_ids"]!=["e01-sc02","e01-sc06"]
        or state["cast"]!=["nia","vesper"] or state["anchors"]!=[
            "nia","vesper_mark","desk","cassette"]
        or state["props"]!=["cassette","audio_desk","headphones","studio_monitor"]
        or state["approval"] is not False or state["revision"]!=1
        or state["camera_plan_ref"]!="docs/season-01/e01-camera-engineer.json"
        or state["contact_ref"]!="docs/season-01/nia-vesper-contact.json"
        or state["character_ref"]!="docs/season-01/nia-vesper-identity.json"):
        raise ValueError("shared scene state drift")
    policy=doc["policy"]
    _shape(policy,("one_scene_state","private_personnel_excluded","external_provider_calls",
                   "payment_authorized","release_authorized","operator_intervention_required"),
           "crew governance")
    if policy!={"one_scene_state":True,"private_personnel_excluded":True,
                "external_provider_calls":False,"payment_authorized":False,
                "release_authorized":False,"operator_intervention_required":True}:
        raise ValueError("crew authorization escalation required")
    validate_camera_engineer(camera,identity,contact,scenes,roles,season)
    return doc

def compile_department_handoffs(registry, season, identity, contact, scenes, roles, camera):
    """Produce deterministic department work packets; no provider work is invoked."""
    validate_crew_registry(registry,season,identity,contact,scenes,roles,camera)
    scene=registry["shared_state"]
    anchor_positions={a["id"]:a["xyz"] for a in camera["anchors"]}
    stages={c["id"]:{
        "parent_shot":c["parent_shot"],"camera_xyz_m":c["at"],
        "lens_equiv_mm":c["lens_mm"],"duration_sec":c["seconds"],
        "frame":c["shot_size"],"perception":c["view"],
        "subjects_visible_to_viewer":c["sees"],"focus":c["focus"]
    } for c in camera["cameras"]}
    packets=[]
    for member in registry["registry"]:
        ident=member["id"]
        # A completed handoff is a prepared *plan*, not completed physical work.
        readiness="prepared_plan" if ident in PLANNING else "blocked_on_assets_and_approval"
        if ident=="executive_producer":
            readiness="approval_required"
        details={
            "shots":list(stages),
            "scene_ids":scene["scene_ids"],
            "cast":scene["cast"],
            "markers_m":anchor_positions,
            "camera_setups":stages,
            "camera_visibility_rule":camera["continuity"]["visibility_rule"],
            "dramatic_objective":"Nia asks Vesper for verifiable evidence, without forfeiting personal agency",
            "dialogue_sources":["nia","vesper"] if ident in (
                "thespian_director","sound_department","editor") else [],
            "asset_receipts":[],
        }
        packets.append({
            "department":ident,
            "phase":member["phase"],
            "requires":list(DEPENDENCIES.get(ident,())),
            "task":member["mission"],
            "input_contract":member["input"],
            "output_contract":member["output"],
            "approval_gate":member["approval_gate"],
            "status":readiness,
            "scene_revision":scene["revision"],
            "evidence":{"planning_only":True,"media_asset_ids":[]},
            "brief":details,
        })
    document={
        "version":1, "episode_id":registry["episode_id"],
        "sequence_id":registry["sequence_id"],"visibility":"public",
        "source_hash":digest(registry),
        "camera_hash":digest(camera),
        "sequence_hash":digest(contact),
        "status":"planning_packets_not_performed",
        "departments":packets,
        "gates":{"human_approval":False,"asset_presence":False,
                 "paid_provider_authorization":False,"release":False},
    }
    return document

def validate_handoffs(out, registry, season, identity, contact, scenes, roles, camera):
    expected=compile_department_handoffs(registry,season,identity,contact,scenes,roles,camera)
    if out != expected:
        raise ValueError("crew handoff altered or stale; recompile from canonical inputs")
    return out

def queued_departments(handoffs):
    """Explicit runnable automated jobs: none until humans approve assets/providers."""
    if handoffs["status"]!="planning_packets_not_performed":
        raise ValueError("unsupported handoff state")
    return [d["department"] for d in handoffs["departments"]
            if d["status"]=="authorized"]

def runtime_bridge(handoffs, runtime):
    """Fail closed: expose *only* already-valid authorized runtime jobs."""
    validate_runtime(runtime)
    if runtime["episode_id"]!=handoffs["episode_id"]:
        raise ValueError("production episode mismatch")
    if any(handoffs["gates"].values()):
        raise ValueError("unreviewed handoff gate cannot authorize runtime")
    # The existing runtime remains the sole source of job execution authority.
    # No implicit jobs, fabricated receipts, or approvals are added.
    from .studio_execution import ready_jobs
    return {"episode_id":runtime["episode_id"],
            "eligible_existing_job_ids":ready_jobs(runtime),
            "created_job_ids":[],
            "handoff_status":handoffs["status"]}
