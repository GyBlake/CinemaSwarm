"""Dramaturgical scene assignment is continuous and evidence-honest."""
import copy
import json
from pathlib import Path
import pytest
from cinemaswarm_world.season_handoff import load_handoff
from cinemaswarm_world.character_roles import load_character_roles
from cinemaswarm_world.pilot_scene_roles import validate_scene_roles,observe_scene_roles

ROOT=Path(__file__).resolve().parents[1]
SEASON=load_handoff(ROOT/"docs/season-01/season-handoff.json")
ROLES=load_character_roles(ROOT/"docs/season-01/character-roles.json",SEASON)
PATH=ROOT/"docs/season-01/e01-scene-roles.json"

def sample():
    return json.loads(PATH.read_text(encoding="utf-8"))

def test_valid_scene_drama_and_coverage():
    result=observe_scene_roles(sample(),ROLES,SEASON)
    assert result["scene_count"]==10 and result["shot_count"]==15
    assert result["approved"] is False
    assert result["scenes"][5]["focus"]=="nia"

def test_not_every_awakened_has_system():
    d=sample()
    assert "vesper" not in d["scenes"][2]["participants"]
    assert "vesper" not in d["scenes"][3]["participants"]
    assert "vesper" in d["scenes"][5]["participants"]

def test_no_phantom_approved_scene():
    d=sample();d["scenes"][0]["reviewed"]=True
    with pytest.raises(ValueError,match="approved"):
        validate_scene_roles(d,ROLES,SEASON)

def test_no_unknown_cast():
    d=sample();d["scenes"][1]["participants"].append("new_system_bearer")
    with pytest.raises(ValueError,match="participant"):
        validate_scene_roles(d,ROLES,SEASON)

def test_no_impossible_shot():
    d=sample();d["scenes"][4]["shots"]=["S99"]
    with pytest.raises(ValueError,match="shot"):
        validate_scene_roles(d,ROLES,SEASON)

def test_no_missing_footage():
    d=sample();d["scenes"][9]["shots"]=[]
    with pytest.raises(ValueError,match="shot"):
        validate_scene_roles(d,ROLES,SEASON)

def test_no_missing_viewpoint():
    d=sample();d["scenes"][8]["focus"]="nia"
    with pytest.raises(ValueError,match="focus"):
        validate_scene_roles(d,ROLES,SEASON)

def test_no_false_render_readiness():
    d=sample();d["requirements"]["render_ready"]=True
    with pytest.raises(ValueError,match="released"):
        validate_scene_roles(d,ROLES,SEASON)

def test_nia_and_vesper_identity_at_threshold():
    d=sample();d["scenes"][5]["participants"].remove("vesper")
    with pytest.raises(ValueError,match="companion"):
        validate_scene_roles(d,ROLES,SEASON)
