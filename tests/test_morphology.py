"""Narrative morphology and originality-gate regression tests."""
import json
import subprocess
import sys
from pathlib import Path

import pytest
from cinemaswarm_world.morphology import (
    load_candidate, load_library, originality_report, structural_similarity,
)


BASE = {
    "version": 1, "story_id": "hidden-executive",
    "beats": [
        {"function": "setup", "actor_role": "protagonist", "outcome": "loss", "cause": None},
        {"function": "betrayal", "actor_role": "antagonist", "outcome": "separation", "cause": 0},
        {"function": "revelation", "actor_role": "protagonist", "outcome": "discovery", "cause": 1},
        {"function": "reversal", "actor_role": "protagonist", "outcome": "gain", "cause": 2},
    ],
}


def cosmetic_variant():
    other = json.loads(json.dumps(BASE))
    other["story_id"] = "royal-android"
    other["setting"] = "underwater kingdom"
    other["dialogue"] = "You are not who you seem."
    other["beats"][0]["visual_style"] = "anime"
    return other


def different_story():
    return {
        "version": 1, "story_id": "mapping-mystery",
        "beats": [
            {"function": "setup", "actor_role": "ensemble", "outcome": "uncertain", "cause": None},
            {"function": "inciting_incident", "actor_role": "ally", "outcome": "discovery", "cause": 0},
            {"function": "choice", "actor_role": "protagonist", "outcome": "sacrifice", "cause": 1},
            {"function": "aftermath", "actor_role": "ensemble", "outcome": "alliance", "cause": 2},
        ],
    }


def test_cosmetic_changes_preserve_structural_identity():
    assert structural_similarity(BASE, cosmetic_variant()) == 1.0
    report = originality_report(cosmetic_variant(), [BASE])
    assert report["blocked"]
    assert report["matches"][0]["story_id"] == "hidden-executive"


def test_causal_and_functional_changes_clear_gate():
    report = originality_report(different_story(), [BASE])
    assert not report["blocked"]
    assert report["highest_similarity"] < report["threshold"]


def test_validators_reject_unanchored_and_forward_causality():
    bad = json.loads(json.dumps(BASE))
    bad["beats"][1]["cause"] = 3
    with pytest.raises(ValueError, match="earlier"):
        structural_similarity(bad, BASE)
    bad["beats"][1]["cause"] = None
    bad["beats"][2]["cause"] = None
    bad["beats"][3]["cause"] = None
    with pytest.raises(ValueError, match="causal"):
        structural_similarity(bad, BASE)


def test_annotated_library_validation(tmp_path):
    candidate_file = tmp_path / "candidate.json"
    library_file = tmp_path / "library.json"
    candidate_file.write_text(json.dumps(BASE))
    library_file.write_text(json.dumps({"version": 1, "stories": [cosmetic_variant()]}))
    assert load_candidate(candidate_file)["story_id"] == BASE["story_id"]
    assert len(load_library(library_file)) == 1


def test_cli_blocks_cosmetic_repetition_before_provider(tmp_path):
    candidate, library = tmp_path / "candidate.json", tmp_path / "library.json"
    candidate.write_text(json.dumps(cosmetic_variant()))
    library.write_text(json.dumps({"version": 1, "stories": [BASE]}))
    script = Path(__file__).resolve().parents[1] / "cinema_swarm.py"
    result = subprocess.run(
        [sys.executable, str(script), "--dry-run", "--morphology-candidate",
         str(candidate), "--morphology-library", str(library)],
        capture_output=True, text=True, cwd=tmp_path, check=False,
    )
    assert result.returncode == 3
    assert "Originality gate blocked" in result.stderr
    assert not (tmp_path / "pilot_sequence.md").exists()


def test_cli_allows_distinct_structure_in_offline_preview(tmp_path):
    candidate, library = tmp_path / "candidate.json", tmp_path / "library.json"
    candidate.write_text(json.dumps(different_story()))
    library.write_text(json.dumps({"version": 1, "stories": [BASE]}))
    script = Path(__file__).resolve().parents[1] / "cinema_swarm.py"
    result = subprocess.run(
        [sys.executable, str(script), "--dry-run", "--morphology-candidate",
         str(candidate), "--morphology-library", str(library)],
        capture_output=True, text=True, cwd=tmp_path, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "NARRATIVE MORPHOLOGY" in result.stdout
    assert "mapping-mystery" in result.stdout


def test_requires_both_files(tmp_path):
    script = Path(__file__).resolve().parents[1] / "cinema_swarm.py"
    result = subprocess.run(
        [sys.executable, str(script), "--dry-run",
         "--morphology-candidate", str(tmp_path / "missing.json")],
        capture_output=True, text=True, cwd=tmp_path, check=False,
    )
    assert result.returncode == 2
    assert "both" in result.stderr
