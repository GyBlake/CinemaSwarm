"""Camera Engineer stack: optics, action axis and subjective AI visibility."""
import copy
import json
from pathlib import Path
import pytest
from cinemaswarm_world.season_handoff import load_handoff
from cinemaswarm_world.character_roles import load_character_roles
from cinemaswarm_world.pilot_scene_roles import load_scene_roles
from cinemaswarm_world.camera_engineer import validate_camera_engineer,load_camera_engineer

BASE=Path(__file__).resolve().parents[1]/"docs/season-01"
SEASON=load_handoff(BASE/"season-handoff.json")
ROLES=load_character_roles(BASE/"character-roles.json",SEASON)
SCENES=load_scene_roles(BASE/"e01-scene-roles.json",ROLES,SEASON)
IDENTITY=json.loads((BASE/"nia-vesper-identity.json").read_text())
PROOF=json.loads((BASE/"nia-vesper-contact.json").read_text())
PATH=BASE/"e01-camera-engineer.json"

def sample():
    return json.loads(PATH.read_text())

def test_valid_geometry_and_coverage():
    result=load_camera_engineer(PATH,IDENTITY,PROOF,SCENES,ROLES,SEASON)
    assert result["total_seconds"]==40
    assert result["status"]=="geometry_checks_passed_not_filmed"
    assert len(result["camera_setups"])==6
    assert all(c["axis_signed_area"]<0 for c in result["camera_setups"])

def test_s10_three_setups_account_for_17_seconds():
    d=sample()
    assert [x["seconds"] for x in d["cameras"] if x["parent_shot"]=="S10"]==[7,5,5]
    validate_camera_engineer(d,IDENTITY,PROOF,SCENES,ROLES,SEASON)

def test_crossing_action_axis_rejected():
    d=sample();d["cameras"][0]["at"]=[2.3,4.7,1.53]
    with pytest.raises(ValueError,match="action axis"):
        validate_camera_engineer(d,IDENTITY,PROOF,SCENES,ROLES,SEASON)

def test_vesper_visible_to_viewer():
    d=sample();d["cameras"][2]["sees"]=["nia"]
    with pytest.raises(ValueError,match="audience cannot see"):
        validate_camera_engineer(d,IDENTITY,PROOF,SCENES,ROLES,SEASON)

def test_vesper_not_visible_to_objective():
    d=sample();d["cameras"][3]["view"]="objective"
    with pytest.raises(ValueError,match="objective camera"):
        validate_camera_engineer(d,IDENTITY,PROOF,SCENES,ROLES,SEASON)

def test_missing_camera_department():
    d=sample();d["departments"]=d["departments"][:-1]
    with pytest.raises(ValueError,match="crew"):
        validate_camera_engineer(d,IDENTITY,PROOF,SCENES,ROLES,SEASON)

def test_invalid_lens():
    d=sample();d["cameras"][1]["lens_mm"]=900
    with pytest.raises(ValueError,match="optics"):
        validate_camera_engineer(d,IDENTITY,PROOF,SCENES,ROLES,SEASON)

def test_wrong_focus():
    d=sample();d["cameras"][0]["focus"]=["missing"]
    with pytest.raises(ValueError,match="focus"):
        validate_camera_engineer(d,IDENTITY,PROOF,SCENES,ROLES,SEASON)

def test_wrong_duration():
    d=sample();d["cameras"][2]["seconds"]=8
    with pytest.raises(ValueError,match="timing"):
        validate_camera_engineer(d,IDENTITY,PROOF,SCENES,ROLES,SEASON)

def test_false_release_approval():
    d=sample();d["approval"]["visual_assets_verified"]=True
    with pytest.raises(ValueError,match="unverified"):
        validate_camera_engineer(d,IDENTITY,PROOF,SCENES,ROLES,SEASON)

def test_false_stage_survey():
    d=sample();d["coordinate_system"]["surveyed"]=True
    with pytest.raises(ValueError,match="coordinates"):
        validate_camera_engineer(d,IDENTITY,PROOF,SCENES,ROLES,SEASON)

def test_invalid_eyeline_pair():
    d=sample();d["continuity"]["eye_match"]["objective_shot"]="S04"
    with pytest.raises(ValueError,match="eyeline"):
        validate_camera_engineer(d,IDENTITY,PROOF,SCENES,ROLES,SEASON)
