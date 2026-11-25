"""Role taxonomy integrated with Æclyptic Season 01 canonical handoff."""
import copy
import json
from pathlib import Path
import pytest
from cinemaswarm_world.season_handoff import load_handoff
from cinemaswarm_world.character_roles import validate_character_roles,character_role_observer

ROOT=Path(__file__).resolve().parents[1]
SEASON=load_handoff(ROOT/"docs/season-01/season-handoff.json")
PATH=ROOT/"docs/season-01/character-roles.json"

def load():
    return json.loads(PATH.read_text(encoding="utf-8"))

def test_complete_taxonomy_and_cast():
    doc=validate_character_roles(load(),SEASON)
    assert len(doc["taxonomy"])>=40
    assert len(doc["characters"])>=15
    assert len(doc["relationships"])>=10

def test_nexus_unique_and_companion_role():
    observer=character_role_observer(load(),SEASON)
    assert observer["point_of_view"]=="nia"
    assert observer["nexus_companion"]=="vesper"
    assert any("primary_antagonist" in x["dramatic_functions"] for x in observer["characters"])

def test_wrong_system_host_rejected():
    doc=load()
    doc["policies"]["nexus_host_id"]="mateo"
    with pytest.raises(ValueError,match="Nexus/protagonist"):
        validate_character_roles(doc,SEASON)

def test_second_protagonist_rejected():
    doc=load()
    doc["characters"][2]["roles"].append("protagonist")
    with pytest.raises(ValueError,match="sole protagonist"):
        validate_character_roles(doc,SEASON)

def test_private_names_rejected():
    doc=load()
    doc["characters"][0]["canon"]="Dreamcorp confidential"
    with pytest.raises(ValueError,match="private"):
        validate_character_roles(doc,SEASON)

def test_unknown_relationship_endpoint_rejected():
    doc=load()
    doc["relationships"][0]["to"]="nonexistent"
    with pytest.raises(ValueError,match="endpoint"):
        validate_character_roles(doc,SEASON)

def test_unapproved_romance_rejected():
    doc=load()
    doc["policies"]["romance"]="nia-mateo"
    with pytest.raises(ValueError,match="policy"):
        validate_character_roles(doc,SEASON)

def test_no_auto_locking_of_creative_roles():
    doc=load()
    doc["characters"][0]["approved"]=True
    with pytest.raises(ValueError,match="unapproved"):
        validate_character_roles(doc,SEASON)

def test_institution_cannot_be_companion():
    doc=load()
    next(x for x in doc["characters"] if x["id"]=="quiet_index")["roles"].append("companion")
    with pytest.raises(ValueError,match="non-person"):
        validate_character_roles(doc,SEASON)

def test_relationship_timeline_validated():
    doc=load()
    doc["relationships"][0]["first_episode"]="e08-aecluptic"
    doc["relationships"][0]["last_episode"]="e01-totality"
    with pytest.raises(ValueError,match="timeline"):
        validate_character_roles(doc,SEASON)
