"""Full studio crew registry and deterministic stage/production handoffs."""
import json
from pathlib import Path
import pytest
from cinemaswarm_world.season_handoff import load_handoff
from cinemaswarm_world.character_roles import load_character_roles
from cinemaswarm_world.pilot_scene_roles import load_scene_roles
from cinemaswarm_world.studio_crew import (
    CREW,validate_crew_registry,compile_department_handoffs,
    validate_handoffs,queued_departments,runtime_bridge,
)

BASE=Path(__file__).resolve().parents[1]/"docs/season-01"
SEASON=load_handoff(BASE/"season-handoff.json")
ROLES=load_character_roles(BASE/"character-roles.json",SEASON)
SCENES=load_scene_roles(BASE/"e01-scene-roles.json",ROLES,SEASON)
IDENTITY=json.loads((BASE/"nia-vesper-identity.json").read_text())
PROOF=json.loads((BASE/"nia-vesper-contact.json").read_text())
CAMERA=json.loads((BASE/"e01-camera-engineer.json").read_text())

def registry():
    return json.loads((BASE/"studio-crew.json").read_text())

def prepared():
    d=registry()
    return compile_department_handoffs(d,SEASON,IDENTITY,PROOF,SCENES,ROLES,CAMERA)

def test_deterministic_full_crew_compilation():
    d=registry()
    assert len(d["registry"])==18
    assert [x["id"] for x in d["registry"]]==list(CREW)
    a=prepared();b=prepared()
    assert a==b
    assert len(a["departments"])==18
    assert a["status"]=="planning_packets_not_performed"
    assert queued_departments(a)==[]

def test_actual_shared_camera_and_actor_positions():
    a=prepared()
    camera=next(x for x in a["departments"] if x["department"]=="camera_operator")
    stage=next(x for x in a["departments"] if x["department"]=="stage_manager")
    actor=next(x for x in a["departments"] if x["department"]=="thespian_director")
    assert camera["brief"]["camera_setups"]==stage["brief"]["camera_setups"]
    assert stage["brief"]["markers_m"]==actor["brief"]["markers_m"]
    assert camera["brief"]["camera_setups"]["S10-B"]["subjects_visible_to_viewer"]==["vesper"]

def test_authorization_never_assumed():
    a=prepared()
    assert a["gates"]=={"human_approval":False,"asset_presence":False,
                        "paid_provider_authorization":False,"release":False}
    assert all(x["status"]!="authorized" for x in a["departments"])

def test_missing_stagehands_rejected():
    d=registry();d["registry"]=[x for x in d["registry"] if x["id"]!="stage_manager"]
    with pytest.raises(ValueError,match="crew"):
        validate_crew_registry(d,SEASON,IDENTITY,PROOF,SCENES,ROLES,CAMERA)

def test_new_nexus_companion_rejected():
    d=registry();d["shared_state"]["cast"]=["nia","vesper","other"]
    with pytest.raises(ValueError,match="scene state"):
        validate_crew_registry(d,SEASON,IDENTITY,PROOF,SCENES,ROLES,CAMERA)

def test_missing_props_rejected():
    d=registry();d["shared_state"]["props"]=[]
    with pytest.raises(ValueError,match="scene state"):
        validate_crew_registry(d,SEASON,IDENTITY,PROOF,SCENES,ROLES,CAMERA)

def test_unapproved_paid_generation_rejected():
    d=registry();d["policy"]["payment_authorized"]=True
    with pytest.raises(ValueError,match="authorization"):
        validate_crew_registry(d,SEASON,IDENTITY,PROOF,SCENES,ROLES,CAMERA)

def test_private_registry_content_rejected():
    d=registry();d["registry"][0]["mission"]="private Dreamcorp agent identity"
    with pytest.raises(ValueError,match="private"):
        validate_crew_registry(d,SEASON,IDENTITY,PROOF,SCENES,ROLES,CAMERA)

def test_changed_camera_hash_invalidates_receipt():
    d=registry()
    a=prepared();a["camera_hash"]="0"*64
    with pytest.raises(ValueError,match="stale"):
        validate_handoffs(a,d,SEASON,IDENTITY,PROOF,SCENES,ROLES,CAMERA)

def test_unapproved_phase_cannot_run():
    a=prepared();a["departments"][11]["status"]="authorized"
    with pytest.raises(ValueError,match="unverified crew authorization"):
        queued_departments(a)
    with pytest.raises(ValueError,match="stale"):
        validate_handoffs(a,registry(),SEASON,IDENTITY,PROOF,SCENES,ROLES,CAMERA)

def test_reject_runtime_mismatched_episode():
    a=prepared()
    with pytest.raises(ValueError):
        runtime_bridge(a,{"episode_id":"other"})

def test_do_not_auto_create_jobs():
    a=prepared()
    r={"version":1,"episode_id":"e01-totality","visibility":"public",
       "budget_limit_usd":0,"assets":[],"jobs":[],"checkpoints":[]}
    result=runtime_bridge(a,r)
    assert result["eligible_existing_job_ids"]==[]
    assert result["created_job_ids"]==[]
