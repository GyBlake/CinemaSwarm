"""Identity-state world projection and explicit provider approval."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from cinemaswarm_world import World, Character, Event
from cinemaswarm_world.identity import Identity, Mutation, IdentityRegistry
from cinemaswarm_world.identity_adapter import load_identity_snapshot, project_identities


T0 = "2026-01-01T00:00:00Z"
T1 = "2026-01-02T00:00:00Z"


def build(tmp_path):
    world = World("lantern-city", T0)
    world.instantiate(Character("mara", "Mara", T0))
    world.pulse(T1, [Event("reveal-1", T1, "mara", "revelation",
                           detail="The map vanished", provenance="approved-script")])
    registry = IdentityRegistry([Identity("mara", "Mara", T0, "face:mara", "voice:mara", "body:mara")], T0)
    registry.pulse(T1, [
        Mutation("coat", T1, "mara", "appearance", {"clothing": "red coat"}, "approved-script")
    ])
    worldfile, identityfile = tmp_path / "world.json", tmp_path / "identity.json"
    worldfile.write_text(world.to_json())
    identityfile.write_text(registry.to_json())
    return worldfile, identityfile


def test_projection_selects_current_mutable_state(tmp_path):
    wf, identity = build(tmp_path)
    payload = project_identities(json.loads(wf.read_text()), load_identity_snapshot(identity))
    assert payload["characters"]["mara"]["appearance"]["clothing"] == "red coat"
    assert payload["characters"]["mara"]["canonical_name"] == "Mara"


def test_tampered_identity_snapshot_rejected(tmp_path):
    _, path = build(tmp_path)
    payload = json.loads(path.read_text())
    payload["view"]["mara"]["voice_anchor"] = "counterfeit"
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="replay"):
        load_identity_snapshot(path)


def test_identity_time_and_names_must_match(tmp_path):
    wf, ip = build(tmp_path)
    doc = json.loads(wf.read_text())
    doc["characters"]["mara"]["name"] = "Someone else"
    with pytest.raises(ValueError, match="name mismatch"):
        project_identities(doc, load_identity_snapshot(ip))
    doc["characters"]["mara"]["name"] = "Mara"
    doc["time"] = "2026-01-03T00:00:00Z"
    with pytest.raises(ValueError, match="same UTC time"):
        project_identities(doc, load_identity_snapshot(ip))


def test_cli_preview_and_live_guard(tmp_path):
    world, identity = build(tmp_path)
    script = Path(__file__).resolve().parents[1] / "cinema_swarm.py"
    args = [sys.executable, str(script), "--world-snapshot", str(world),
            "--identity-snapshot", str(identity)]
    dry = subprocess.run(args + ["--dry-run"], cwd=tmp_path,
                         capture_output=True, text=True, check=False)
    assert dry.returncode == 0, dry.stderr
    assert "CHARACTER IDENTITY & EMBODIMENT" in dry.stdout
    assert "red coat" in dry.stdout
    live = subprocess.run(args + ["--approve-world-brief"], cwd=tmp_path,
                          capture_output=True, text=True, check=False)
    assert live.returncode == 2
    assert "--approve-identity-brief" in live.stderr
    assert not (tmp_path / "pilot_sequence.md").exists()


def test_identity_requires_world(tmp_path):
    _, identity = build(tmp_path)
    script = Path(__file__).resolve().parents[1] / "cinema_swarm.py"
    r = subprocess.run([sys.executable, str(script), "--identity-snapshot", str(identity), "--dry-run"],
                       cwd=tmp_path, capture_output=True, text=True, check=False)
    assert r.returncode == 2
    assert "requires --world-snapshot" in r.stderr
