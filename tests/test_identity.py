"""Identity continuity: immutable anchors, bodies, inventory and replay."""
import copy
import json
import pytest

from cinemaswarm_world.identity import Identity, IdentityRegistry, Mutation

T0 = "2026-01-01T00:00:00Z"
T1 = "2026-01-02T00:00:00Z"


def registry():
    return IdentityRegistry([
        Identity("mara", "Mara", T0, "sha256:face-mara", "voice:signature-mara", "body-mara"),
        Identity("kai", "Kai", T0, "sha256:face-kai", "voice:signature-kai", "body-kai"),
    ], T0)


def change(name, actor, action, data, at=T1):
    return Mutation(name, at, actor, action, data, "approved-series-canon")


def test_identity_preserved_through_swap_and_costume():
    reg = registry()
    reg.pulse(T1, [
        change("e1", "mara", "appearance", {"clothing": "red jacket", "image_variant": "asset:coat-v1"}),
        change("e2", "mara", "body_measure", {"weight_kg": 72, "height_cm": 176, "muscle": "toned"}),
        change("e3", "mara", "body_swap", {"with": "kai"}),
        change("e4", "mara", "voice_delivery", {"style": "whisper", "pitch_shift": -2}),
    ])
    mara = reg.view["mara"]
    assert mara["current_body"] == "body-kai"
    assert reg.view["kai"]["current_body"] == "body-mara"
    assert mara["canonical_name"] == "Mara"
    assert mara["face_anchor"] == "sha256:face-mara"
    assert mara["voice_anchor"] == "voice:signature-mara"
    assert mara["appearance"]["clothing"] == "red jacket"
    assert mara["voice_delivery"]["style"] == "whisper"
    assert IdentityRegistry.hydrate(json.loads(reg.to_json())).snapshot() == reg.snapshot()


def test_items_require_ownership_slots_and_recovery():
    reg = registry()
    reg.pulse(T1, [change("item1", "mara", "item",
                          {"id": "amulet", "condition": "intact", "status": "equipped", "slot": "neck"})])
    first = reg.snapshot()
    with pytest.raises(ValueError, match="slot"):
        reg.commit(change("item2", "mara", "item",
                          {"id": "badge", "condition": "intact", "status": "equipped", "slot": "neck"}))
    assert reg.snapshot() == first
    reg.commit(change("item3", "mara", "item",
                      {"id": "amulet", "condition": "damaged", "status": "lost"}))
    with pytest.raises(ValueError, match="recovery"):
        reg.commit(change("item4", "mara", "item",
                          {"id": "amulet", "condition": "damaged", "status": "equipped", "slot": "neck"}))
    reg.commit(change("item5", "mara", "item",
                      {"id": "amulet", "condition": "enhanced", "status": "equipped", "slot": "neck",
                       "recovered": True}))
    assert reg.view["mara"]["inventory"]["amulet"]["condition"] == "enhanced"


def test_skills_and_relationships_state_changes():
    reg = registry()
    reg.pulse(T1, [
        change("s1", "mara", "skill", {"id": "navigation", "status": "learned"}),
        change("s2", "mara", "skill", {"id": "navigation", "status": "equipped"}),
        change("r1", "mara", "relation", {"target": "kai", "status": "trusted"}),
        change("r2", "mara", "relation", {"target": "kai", "status": "estranged"}),
    ])
    assert reg.view["mara"]["skills"]["navigation"] == "equipped"
    assert reg.view["mara"]["relationships"]["kai"] == "estranged"


def test_atomic_pulse_and_tamper_detection():
    reg = registry()
    original = reg.snapshot()
    with pytest.raises(ValueError, match="unknown"):
        reg.pulse(T1, [change("valid", "mara", "alias", {"name": "The Navigator"}),
                       change("bad", "unseen", "alias", {"name": "Shadow"})])
    assert reg.snapshot() == original
    reg.pulse(T1, [change("ok", "mara", "alias", {"name": "The Navigator"})])
    tampered = reg.snapshot()
    tampered["view"]["mara"]["canonical_name"] = "Someone Else"
    with pytest.raises(ValueError, match="differs"):
        IdentityRegistry.hydrate(tampered)


def test_second_body_occupancy_rejected_and_safely_reassigned():
    reg = registry()
    reg.pulse(T1, [])
    with pytest.raises(ValueError, match="occupied"):
        reg.commit(change("e1", "mara", "embody", {"body_id": "body-kai"}))
    reg.commit(change("e2", "mara", "embody", {"body_id": "body-new"}))
    assert reg.view["mara"]["current_body"] == "body-new"
    assert reg.view["kai"]["current_body"] == "body-kai"


def test_unchanged_original_legacy_world():
    from cinemaswarm_world import World, Character
    world = World("classic", T0)
    world.instantiate(Character("mara", "Mara", T0))
    assert world.snapshot()["characters"]["mara"]["name"] == "Mara"
