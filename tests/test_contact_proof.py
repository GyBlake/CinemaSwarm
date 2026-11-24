"""Previsualization evidence gates: Nexus contact sequence remains private and unrendered."""
import json
from pathlib import Path
import pytest

from cinemaswarm_world.season_handoff import load_handoff
from cinemaswarm_world.character_roles import load_character_roles
from cinemaswarm_world.pilot_scene_roles import load_scene_roles
from cinemaswarm_world.contact_proof import validate_contact,load_contact

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"docs/season-01"
SEASON=load_handoff(BASE/"season-handoff.json")
ROLES=load_character_roles(BASE/"character-roles.json",SEASON)
SCENES=load_scene_roles(BASE/"e01-scene-roles.json",ROLES,SEASON)

def docs():
    return (json.loads((BASE/"nia-vesper-identity.json").read_text(encoding="utf-8")),
            json.loads((BASE/"nia-vesper-contact.json").read_text(encoding="utf-8")))

def test_contact_is_consistent_four_shots():
    a,b=docs()
    assert validate_contact(a,b,SCENES,ROLES,SEASON)["target_seconds"]==40
    assert load_contact(BASE/"nia-vesper-identity.json",BASE/"nia-vesper-contact.json",SCENES,ROLES,SEASON)

def test_vocal_identity_not_interchangeable():
    a,b=docs();a["subjects"][1]["id"]="alternate"
    with pytest.raises(ValueError,match="host or voice"):
        validate_contact(a,b,SCENES,ROLES,SEASON)

def test_system_absent_from_objective_camera():
    a,b=docs();b["shots"][3]["view"]="subjective"
    with pytest.raises(ValueError,match="image leak"):
        validate_contact(a,b,SCENES,ROLES,SEASON)

def test_vocal_leak_prohibited():
    a,b=docs();b["shots"][1]["dialogue"].append({"speaker":"vesper","line":"I am here"})
    with pytest.raises(ValueError,match="neutral camera"):
        validate_contact(a,b,SCENES,ROLES,SEASON)

def test_exact_timing():
    a,b=docs();b["shots"][0]["seconds"]=10
    with pytest.raises(ValueError,match="duration mismatch"):
        validate_contact(a,b,SCENES,ROLES,SEASON)

def test_no_fake_render_completion():
    a,b=docs();b["production"]["rendered_video"]=True
    with pytest.raises(ValueError,match="unverified"):
        validate_contact(a,b,SCENES,ROLES,SEASON)

def test_no_payment_authorization():
    a,b=docs();b["production"]["paid_generation_authorized"]=True
    with pytest.raises(ValueError,match="unverified"):
        validate_contact(a,b,SCENES,ROLES,SEASON)

def test_no_forged_likeness_approval():
    a,b=docs();a["review"]["likeness_approved"]=True
    with pytest.raises(ValueError,match="unreviewed"):
        validate_contact(a,b,SCENES,ROLES,SEASON)

def test_no_unapproved_companion_avatar():
    a,b=docs();a["relationship"]["independent_physical_presence"]=True
    with pytest.raises(ValueError,match="private Nexus"):
        validate_contact(a,b,SCENES,ROLES,SEASON)

def test_no_unreferenced_scene():
    a,b=docs();b["shots"][2]["scene_id"]="e01-sc07"
    with pytest.raises(ValueError,match="cross-scene"):
        validate_contact(a,b,SCENES,ROLES,SEASON)


def test_audience_sees_companion_in_subjective_view():
    a,b=docs()
    assert a["relationship"]["audience_visible"] is True
    assert a["relationship"]["audience_audible"] is True
    assert "humanoid" in b["shots"][2]["effects"].lower()
    validate_contact(a,b,SCENES,ROLES,SEASON)

def test_reject_invisible_to_viewer():
    a,b=docs();a["relationship"]["audience_visible"]=False
    with pytest.raises(ValueError,match="private Nexus"):
        validate_contact(a,b,SCENES,ROLES,SEASON)

def test_reject_invisible_subjective_ai():
    a,b=docs();b["shots"][2]["effects"]="Only a vague empty waveform and glyphs; no character."
    with pytest.raises(ValueError,match="visible companion"):
        validate_contact(a,b,SCENES,ROLES,SEASON)
