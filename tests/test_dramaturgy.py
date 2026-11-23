"""Offline evidence-oriented Semantic Dramaturgy Engine tests."""
import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest
from cinemaswarm_world.dramaturgy import (
    audit_dramaturgy, dramaturgy_context, load_context, validate_context,
)

STORY = {"version": 1, "story_id": "lantern-audit", "beats": [
    {"function": "setup", "actor_role": "protagonist", "outcome": "uncertain", "cause": None},
    {"function": "revelation", "actor_role": "antagonist", "outcome": "discovery", "cause": 0},
    {"function": "choice", "actor_role": "protagonist", "outcome": "sacrifice", "cause": 1},
    {"function": "aftermath", "actor_role": "ensemble", "outcome": "alliance", "cause": 2},
]}
CONTEXT = {"version": 1, "story_id": "lantern-audit", "reviewed": True,
           "characters": ["mara", "archivist"],
           "facts": [{"id": "secret-map", "introduced_at": 1, "provenance": "approved-beat-1"}],
           "knowledge": [
               {"beat_index": 1, "audience": ["secret-map"],
                "characters": {"mara": [], "archivist": ["secret-map"]}},
               {"beat_index": 2, "audience": ["secret-map"],
                "characters": {"mara": ["secret-map"], "archivist": ["secret-map"]}},
           ],
           "stakes": [{"id": "archive", "owner": "mara", "introduced_at": 0,
                       "resolved_at": 3, "provenance": "approved-script"}],
           "transformations": [{"character_id": "mara", "from_archetype": "seeker",
                                "to_archetype": "guardian", "beat_index": 2,
                                "provenance": "author-reviewed"}],
           "motifs": [{"id": "map", "beat_indices": [0, 1, 3],
                       "provenance": "approved-script"}]}


def test_dramaturgy_tracks_knowledge_stakes_and_circulation():
    initial = copy.deepcopy(CONTEXT)
    report = audit_dramaturgy(STORY, CONTEXT)
    assert CONTEXT == initial
    assert report["causality"]["causal_density"] == 1
    assert report["causality"]["protagonist_decisions"] == 1
    assert report["knowledge_asymmetries"] == [
        {"beat_index": 1, "character_id": "mara", "fact_id": "secret-map",
         "type": "dramatic_irony", "provenance": "approved-beat-1"}]
    assert report["tce_rci"] == {
        "origination": 2, "sustenance": 2, "transformation": 1, "circulation": 3
    }
    assert report["status"] == "reviewed_annotations"
    assert "SEMANTIC DRAMATURGY AUDIT" in dramaturgy_context(report)


def test_unknown_is_not_assumed_false():
    context = copy.deepcopy(CONTEXT)
    context["knowledge"] = []
    report = audit_dramaturgy(STORY, context)
    assert report["knowledge_asymmetries"] == []
    assert "knowledge_unannotated" in {f["code"] for f in report["findings"]}


def test_unreviewed_annotation_rejected_from_provider_context():
    context = copy.deepcopy(CONTEXT)
    context["reviewed"] = False
    report = audit_dramaturgy(STORY, context)
    with pytest.raises(ValueError, match="unreviewed"):
        dramaturgy_context(report)


@pytest.mark.parametrize("mutation", [
    lambda c: c["knowledge"][0]["audience"].append("future"),
    lambda c: c["facts"][0].update(introduced_at=2),
    lambda c: c["knowledge"][0]["characters"].update(unknown=[]),
    lambda c: c["transformations"][0].update(to_archetype="seeker"),
    lambda c: c["stakes"][0].update(resolved_at=99),
    lambda c: c["motifs"][0].update(beat_indices=[1, 1]),
    lambda c: c.update(story_id="wrong"),
])
def test_invalid_references_rejected(mutation):
    context = copy.deepcopy(CONTEXT)
    mutation(context)
    with pytest.raises(ValueError):
        validate_context(STORY, context)


def test_cli_writes_audit_without_provider(tmp_path):
    candidate = tmp_path / "story.json"
    context = tmp_path / "context.json"
    output = tmp_path / "report.json"
    candidate.write_text(json.dumps(STORY))
    context.write_text(json.dumps(CONTEXT))
    script = Path(__file__).resolve().parents[1] / "cinema_swarm.py"
    call = subprocess.run([sys.executable, str(script), "--audit-dramaturgy", str(candidate),
                           "--dramaturgy-context", str(context),
                           "--dramaturgy-output", str(output)],
                          cwd=tmp_path, capture_output=True, text=True, check=False)
    assert call.returncode == 0, call.stderr
    assert json.loads(output.read_text())["tce_rci"]["circulation"] == 3
    assert not (tmp_path / "pilot_sequence.md").exists()


def test_cli_provider_guard_and_dry_run(tmp_path):
    candidate, context = tmp_path / "story.json", tmp_path / "context.json"
    candidate.write_text(json.dumps(STORY))
    context.write_text(json.dumps(CONTEXT))
    script = Path(__file__).resolve().parents[1] / "cinema_swarm.py"
    command = [sys.executable, str(script), "--dramaturgy-candidate", str(candidate),
               "--dramaturgy-context", str(context)]
    run = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True, check=False)
    assert run.returncode == 2
    assert "--approve-dramaturgy-brief" in run.stderr
    dry = subprocess.run(command + ["--dry-run"], cwd=tmp_path,
                         capture_output=True, text=True, check=False)
    assert dry.returncode == 0, dry.stderr
    assert "SEMANTIC DRAMATURGY AUDIT" in dry.stdout


def test_cli_requires_both_inputs(tmp_path):
    script = Path(__file__).resolve().parents[1] / "cinema_swarm.py"
    result = subprocess.run([sys.executable, str(script), "--dry-run",
                             "--dramaturgy-candidate", "missing.json"],
                            cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 2
    assert "both" in result.stderr


def test_audit_flags_possible_memory_discontinuity_not_fabricated_forgetting():
    context = copy.deepcopy(CONTEXT)
    context["knowledge"][1]["characters"]["archivist"] = []
    report = audit_dramaturgy(STORY, context)
    assert report["knowledge_discontinuities"] == [{
        "character_id": "archivist", "fact_id": "secret-map",
        "previous_beat": 1, "beat_index": 2,
        "provenance": "approved-beat-1",
    }]
    assert "knowledge_discontinuity" in {f["code"] for f in report["findings"]}


def test_unreviewed_context_cannot_pass_cli_even_with_approval_flag(tmp_path):
    candidate, context = tmp_path / "story.json", tmp_path / "context.json"
    candidate.write_text(json.dumps(STORY))
    annotations = copy.deepcopy(CONTEXT)
    annotations["reviewed"] = False
    context.write_text(json.dumps(annotations))
    script = Path(__file__).resolve().parents[1] / "cinema_swarm.py"
    call = subprocess.run(
        [sys.executable, str(script), "--dramaturgy-candidate", str(candidate),
         "--dramaturgy-context", str(context), "--approve-dramaturgy-brief"],
        cwd=tmp_path, capture_output=True, text=True, check=False,
    )
    assert call.returncode == 2
    assert "unreviewed" in call.stderr
    assert not (tmp_path / "pilot_sequence.md").exists()


def test_dramaturgy_audit_refuses_overwrite(tmp_path):
    candidate, context, output = (tmp_path / n for n in ("story.json", "context.json", "audit.json"))
    candidate.write_text(json.dumps(STORY))
    context.write_text(json.dumps(CONTEXT))
    output.write_text("original")
    script = Path(__file__).resolve().parents[1] / "cinema_swarm.py"
    call = subprocess.run(
        [sys.executable, str(script), "--audit-dramaturgy", str(candidate),
         "--dramaturgy-context", str(context), "--dramaturgy-output", str(output)],
        cwd=tmp_path, capture_output=True, text=True, check=False,
    )
    assert call.returncode == 2
    assert output.read_text() == "original"
