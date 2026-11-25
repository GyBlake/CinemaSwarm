"""Offline verification: event chronology, identity, provenance, circulation."""
import copy
import json
import pytest

from cinemaswarm_world import Character, Event, World


def make_world():
    world = World("lantern-city", "2026-01-01T00:00:00Z")
    world.instantiate(Character(
        "cartographer", "The Cartographer", "2026-01-01T00:00:00+00:00",
        archetypes=["seeker"],
        symbolic_profile={"astrology": {"source": "author-supplied"}, "numerology": {"role": "fiction"}},
        motivations=["map the city"],
    ))
    return world


def test_instantiation_and_symbolic_metadata():
    world = make_world()
    assert world.snapshot()["characters"]["cartographer"]["archetypes"] == ["seeker"]
    assert world.snapshot()["characters"]["cartographer"]["symbolic_profile"]["numerology"]["role"] == "fiction"
    with pytest.raises(ValueError, match="duplicate"):
        world.instantiate(Character("cartographer", "Other", world.time))


def test_pulse_circulation_and_narrative_observer():
    world = make_world()
    event = Event("e1", "2026-01-02T10:00:00Z", "cartographer", "revelation",
                  detail="The map changed after the blackout.", provenance="script-approved")
    assert world.pulse("2026-01-02T10:00:00Z", [event]) == {
        "origination": 1, "sustenance": 1, "transformation": 1, "circulation": 1
    }
    assert world.narrative_observer()[0]["provenance"] == "script-approved"
    assert "map changed" in world.characters["cartographer"].memories[0]
    assert json.loads(world.to_json())["events"][0]["id"] == "e1"


def test_atomic_failure_preserves_world():
    world = make_world()
    before = copy.deepcopy(world.snapshot())
    with pytest.raises(ValueError, match="actor"):
        world.pulse("2026-01-02T00:00:00Z", [
            Event("e1", "2026-01-02T00:00:00Z", "absent", "choice", detail="unverified")
        ])
    assert world.snapshot() == before


def test_prevent_time_travel_duplicate_and_unknown_kind():
    world = make_world()
    with pytest.raises(ValueError, match="offset"):
        Event("e0", "2026-01-01T00:00:00", "cartographer", "choice")
    with pytest.raises(ValueError, match="backward"):
        world.advance("2025-12-31T23:59:59Z")
    with pytest.raises(ValueError, match="unsupported"):
        world.pulse("2026-01-02T00:00:00Z", [
            Event("e0", "2026-01-02T00:00:00Z", "cartographer", "teleport")
        ])
    assert not world.events


def test_relationship_and_snapshot_are_detached():
    world = make_world()
    world.instantiate(Character("archivist", "The Archivist", world.time))
    world.pulse("2026-01-02T00:00:00Z", [
        Event("e2", "2026-01-02T00:00:00Z", "cartographer", "relationship",
              target_id="archivist", detail="Trust is broken")
    ])
    snap = world.snapshot()
    snap["characters"]["cartographer"]["memories"].clear()
    assert world.characters["cartographer"].memories == ["Trust is broken"]
    assert world.characters["cartographer"].relationships["archivist"] == "Trust is broken"
