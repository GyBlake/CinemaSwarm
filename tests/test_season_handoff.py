"""Season 01 handoff regression: honest delivery state and protagonist System."""
import copy
import json
from pathlib import Path
import pytest
from cinemaswarm_world.season_handoff import load_handoff, validate_season_handoff

PATH=Path(__file__).resolve().parents[1]/"docs/season-01/season-handoff.json"

def source():
    return json.loads(PATH.read_text(encoding="utf-8"))

def test_canonical_package():
    d=load_handoff(PATH)
    assert d["protagonist"]["system_voice"]=="vesper"
    assert len(d["episodes"])==8
    assert sum(x["nexus"] for x in d["cast"])==1

def test_no_false_media_claim():
    d=source()
    d["production"]["finished_episodes"]=8
    with pytest.raises(ValueError,match="release claim"):
        validate_season_handoff(d)

def test_no_secondary_systems():
    d=source()
    d["cast"][1]["system"]="another-ai"
    with pytest.raises(ValueError,match="non-bearer"):
        validate_season_handoff(d)

def test_no_phantom_authorization():
    d=source()
    d["production_release_authorized"]=True
    with pytest.raises(ValueError,match="draft cannot"):
        validate_season_handoff(d)

def test_all_eight_treatments_not_scripts():
    d=source()
    d["episodes"][3]["screenplay_state"]="complete"
    with pytest.raises(ValueError,match="script state"):
        validate_season_handoff(d)

def test_cannot_rename_nexus_companion_without_lineage():
    d=source()
    d["protagonist"]["system_voice"]="other"
    with pytest.raises(ValueError,match="companion mismatch"):
        validate_season_handoff(d)
