"""Offline contract tests for the snapshot → narrative → Showrunner connection."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from cinemaswarm_world import Character, Event, World
from cinemaswarm_world.adapter import build_world_request, load_world_snapshot, observer_payload


def sample(tmp_path):
    world = World("lantern-city", "2026-01-01T00:00:00Z")
    world.instantiate(Character("mapmaker", "Mapmaker", world.time,
                               archetypes=["seeker"], motivations=["restore maps"]))
    world.pulse("2026-01-02T00:00:00Z", [
        Event("reveal-1", "2026-01-02T00:00:00Z", "mapmaker", "revelation",
              detail="The avenue vanished.", provenance="approved-test-brief")
    ])
    path = tmp_path / "world.json"
    path.write_text(world.to_json(), encoding="utf-8")
    return path


def test_world_observer_and_provenance(tmp_path):
    state = load_world_snapshot(sample(tmp_path))
    payload = observer_payload(state)
    assert payload["observed_events"][0]["provenance"] == "approved-test-brief"
    assert payload["characters"]["mapmaker"]["archetypes"] == ["seeker"]
    request = build_world_request("A city changes", state)
    assert "Showrunner" in request and "reveal-1" in request
    assert "The avenue vanished" in request


def test_invalid_snapshot_rejected(tmp_path):
    path = sample(tmp_path)
    state = json.loads(path.read_text())
    state["events"][0]["actor_id"] = "missing"
    path.write_text(json.dumps(state))
    with pytest.raises(ValueError, match="actor"):
        load_world_snapshot(path)


def test_duplicate_event_and_backward_time_rejected(tmp_path):
    state = load_world_snapshot(sample(tmp_path))
    state["events"].append(dict(state["events"][0]))
    with pytest.raises(ValueError, match="duplicate"):
        observer_payload(state)
    state["events"] = state["events"][:1]
    state["time"] = "2025-01-01T00:00:00Z"
    with pytest.raises(ValueError, match="after world time"):
        observer_payload(state)


def test_preview_requires_no_provider(tmp_path):
    path = sample(tmp_path)
    script = Path(__file__).resolve().parents[1] / "cinema_swarm.py"
    result = subprocess.run(
        [sys.executable, str(script), "--world-snapshot", str(path), "--dry-run"],
        capture_output=True, text=True, check=False, cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert "reveal-1" in result.stdout
    assert "WORLD OBSERVER SNAPSHOT" in result.stdout


def test_live_requires_explicit_approval(tmp_path):
    path = sample(tmp_path)
    script = Path(__file__).resolve().parents[1] / "cinema_swarm.py"
    result = subprocess.run(
        [sys.executable, str(script), "--world-snapshot", str(path)],
        capture_output=True, text=True, check=False, cwd=tmp_path,
    )
    assert result.returncode == 2
    assert "--approve-world-brief" in result.stderr
    assert not (tmp_path / "pilot_sequence.md").exists()


def test_ordinary_brief_unchanged():
    from cinema_swarm import build_request, parse_args
    assert "WORLD OBSERVER SNAPSHOT" not in build_request("A story")
    assert parse_args(["--dry-run"]).world_snapshot is None
