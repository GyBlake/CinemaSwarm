"""Cross-vessel asset binding, custody and hydration regression checks."""
import json
import subprocess
import sys
from pathlib import Path

import pytest
from cinemaswarm_world import World, Character, Event
from cinemaswarm_world.identity import Identity, IdentityRegistry, Mutation
from cinemaswarm_world.embodiment import Body, Object, BindingEvent, BindingRegistry, project_embodiment

T0 = "2026-01-01T00:00:00Z"
T1 = "2026-01-02T00:00:00Z"


def setup():
    people = IdentityRegistry([
        Identity("mara", "Mara", T0, "identity-face:mara", "identity-voice:mara", "body-a"),
        Identity("kai", "Kai", T0, "identity-face:kai", "identity-voice:kai", "body-b"),
    ], T0)
    assets = BindingRegistry([
        Body("body-a", "face:body-a", "larynx:body-a", "red coat"),
        Body("body-b", "face:body-b", "larynx:body-b", "blue tunic"),
    ], [
        Object("talisman", "asset:talisman-v1", "intact", "worn",
               holder="body-a", slot="neck", owner="mara")
    ], T0)
    return people, assets


def test_swap_keeps_body_worn_garments_and_preserves_persona():
    people, assets = setup()
    people.pulse(T1, [Mutation("s1", T1, "mara", "body_swap", {"with": "kai"}, "approved")])
    assets.pulse(T1, [])
    projection = project_embodiment(people, assets)
    mara = projection["characters"]["mara"]
    kai = projection["characters"]["kai"]
    assert mara["body_id"] == "body-b"
    assert mara["body"]["clothing"] == "blue tunic"
    assert mara["identity_voice_anchor"] == "identity-voice:mara"
    assert mara["body"]["vocal_anchor"] == "larynx:body-b"
    assert mara["worn"] == {}
    assert kai["worn"]["talisman"]["owner"] == "mara"


def test_body_change_and_item_lifecycle():
    people, assets = setup()
    assets.pulse(T1, [
        BindingEvent("alter", T1, "body_change", "body-a",
                     {"weight_kg": 81, "muscle": "toned", "visual_anchor": "face:body-a-v2"}, "approved"),
        BindingEvent("damage", T1, "object_change", "talisman",
                     {"condition": "damaged"}, "approved"),
        BindingEvent("drop", T1, "object_change", "talisman",
                     {"location": "lost"}, "approved"),
    ])
    people.pulse(T1, [])
    assert project_embodiment(people, assets)["characters"]["mara"]["body"]["weight_kg"] == 81
    assert assets.objects["talisman"]["holder"] is None
    with pytest.raises(ValueError, match="recovery"):
        assets.commit(BindingEvent("bad", T1, "object_change", "talisman",
                                   {"condition": "enhanced", "location": "worn",
                                    "holder": "body-a", "slot": "neck"}, "approved"))
    assets.commit(BindingEvent("return", T1, "object_change", "talisman",
                               {"condition": "enhanced", "location": "worn",
                                "holder": "body-a", "slot": "neck", "recovered": True}, "approved"))
    assert assets.objects["talisman"]["condition"] == "enhanced"
    assert BindingRegistry.hydrate(json.loads(assets.to_json())).snapshot() == assets.snapshot()


def test_conflicting_equipment_rolls_back():
    _, assets = setup()
    original = assets.snapshot()
    with pytest.raises(ValueError, match="slot"):
        assets.pulse(T1, [
            BindingEvent("one", T1, "body_change", "body-a",
                         {"clothing": "green"}, "approved"),
            BindingEvent("two", T1, "object_change", "talisman",
                         {"location": "carried", "holder": "body-b", "slot": None}, "approved"),
            BindingEvent("three", T1, "object_change", "talisman",
                         {"location": "worn", "holder": "body-b", "slot": None}, "approved"),
        ])
    assert assets.snapshot() == original


def test_snapshot_tampering_detected():
    _, assets = setup()
    altered = assets.snapshot()
    altered["bodies"]["body-a"]["clothing"] = "fake"
    with pytest.raises(ValueError, match="replay"):
        BindingRegistry.hydrate(altered)


def test_unknown_body_rejected():
    people, assets = setup()
    people.pulse(T1, [Mutation("new", T1, "mara", "embody", {"body_id": "unknown"}, "approved")])
    assets.pulse(T1, [])
    with pytest.raises(ValueError, match="unknown physical body"):
        project_embodiment(people, assets)


def test_cli_binding_preview_and_guard(tmp_path):
    people, assets = setup()
    world = World("demo", T0)
    world.instantiate(Character("mara", "Mara", T0))
    world.pulse(T1, [Event("e1", T1, "mara", "revelation", detail="A talisman hums", provenance="approved")])
    people.pulse(T1, [])
    assets.pulse(T1, [])
    w, i, a = [tmp_path / name for name in ("world.json", "identity.json", "assets.json")]
    w.write_text(world.to_json())
    i.write_text(people.to_json())
    a.write_text(assets.to_json())
    cli = Path(__file__).resolve().parents[1] / "cinema_swarm.py"
    command = [sys.executable, str(cli), "--world-snapshot", str(w),
               "--identity-snapshot", str(i), "--asset-bindings", str(a)]
    dry = subprocess.run(command + ["--dry-run"], capture_output=True, text=True, cwd=tmp_path)
    assert dry.returncode == 0, dry.stderr
    assert "PHYSICAL EMBODIMENT AND ASSET BINDINGS" in dry.stdout
    assert "talisman" in dry.stdout
    live = subprocess.run(command + ["--approve-world-brief", "--approve-identity-brief"],
                          capture_output=True, text=True, cwd=tmp_path)
    assert live.returncode == 2
    assert "--approve-asset-brief" in live.stderr


def test_asset_binding_requires_identity(tmp_path):
    cli = Path(__file__).resolve().parents[1] / "cinema_swarm.py"
    result = subprocess.run([sys.executable, str(cli), "--asset-bindings", "missing.json", "--dry-run"],
                            capture_output=True, text=True, cwd=tmp_path)
    assert result.returncode == 2
    assert "requires --identity-snapshot" in result.stderr
