"""Literary ontology parser: offline extraction, evidence, review and CLI."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from cinemaswarm_world.literary_parser import extract_draft, finalize_review
from cinemaswarm_world.morphology import validate_story, originality_report


SCRIPT = """TITLE: Lantern City
ROLE Mara: protagonist
ROLE The Director: antagonist

INT. ARCHIVE - NIGHT
Mara discovers that the old map was erased.
EXT. ROOFTOP - NIGHT
The Director betrays Mara and locks the archive.
INT. STATION - DAY
Because of the betrayal, Mara decides to sacrifice her access.
"""


def test_extracts_evidence_and_flags_unapproved_beats():
    review = extract_draft(SCRIPT, "lantern-city")
    assert review["status"] == "needs_review"
    assert [beat["function"] for beat in review["candidate"]["beats"]] == [
        "revelation", "betrayal", "choice"
    ]
    assert review["candidate"]["beats"][2]["cause"] == 1
    assert review["candidate"]["beats"][0]["actor_role"] == "protagonist"
    assert review["candidate"]["beats"][1]["actor_role"] == "other"  # Two names: ambiguity, not invented role
    assert review["evidence"][0]["line"] == 5
    assert all(not item["approved"] for item in review["evidence"])


def test_finalization_requires_every_approval():
    review = extract_draft(SCRIPT, "lantern-city")
    with pytest.raises(ValueError, match="every beat"):
        finalize_review(review)
    for record in review["evidence"]:
        record["approved"] = True
    candidate = finalize_review(review)
    assert validate_story(candidate)
    assert candidate["review_provenance"]["reviewed_beats"] == 3
    assert originality_report(candidate, [candidate])["blocked"]


def test_causal_gap_requires_review_before_finalization():
    source = """ROLE Ada: protagonist
Ada discovers a secret.
Ada betrays the guild.
Ada decides to flee."""
    review = extract_draft(source, "missing-causality")
    for item in review["evidence"]:
        item["approved"] = True
    with pytest.raises(ValueError, match="causal"):
        finalize_review(review)


def test_non_matching_text_does_not_fabricate_story():
    review = extract_draft("INT. ROOM - DAY\nThe lamp is green.", "static")
    assert review["candidate"]["beats"] == []
    with pytest.raises(ValueError):
        finalize_review(review)


def test_cli_two_phase_offline_review_and_gate(tmp_path):
    script = tmp_path / "script.txt"
    review_path = tmp_path / "review.json"
    candidate = tmp_path / "candidate.json"
    library = tmp_path / "library.json"
    script.write_text(SCRIPT, encoding="utf-8")
    cli = Path(__file__).resolve().parents[1] / "cinema_swarm.py"
    first = subprocess.run(
        [sys.executable, str(cli), "--extract-ontology", str(script),
         "--ontology-story-id", "lantern-city", "--ontology-output", str(review_path)],
        cwd=tmp_path, capture_output=True, text=True, check=False,
    )
    assert first.returncode == 0, first.stderr
    draft = json.loads(review_path.read_text(encoding="utf-8"))
    assert draft["status"] == "needs_review"
    second = subprocess.run(
        [sys.executable, str(cli), "--finalize-ontology-review", str(review_path),
         "--ontology-output", str(candidate)],
        cwd=tmp_path, capture_output=True, text=True, check=False,
    )
    assert second.returncode == 2
    assert not candidate.exists()
    for item in draft["evidence"]:
        item["approved"] = True
    review_path.write_text(json.dumps(draft), encoding="utf-8")
    third = subprocess.run(
        [sys.executable, str(cli), "--finalize-ontology-review", str(review_path),
         "--ontology-output", str(candidate)],
        cwd=tmp_path, capture_output=True, text=True, check=False,
    )
    assert third.returncode == 0, third.stderr
    library.write_text(json.dumps({"version": 1, "stories": [json.loads(candidate.read_text())]}))
    gate = subprocess.run(
        [sys.executable, str(cli), "--dry-run", "--morphology-candidate", str(candidate),
         "--morphology-library", str(library)],
        cwd=tmp_path, capture_output=True, text=True, check=False,
    )
    assert gate.returncode == 3
    assert "Originality gate blocked" in gate.stderr


def test_no_overwrite_of_review(tmp_path):
    script = tmp_path / "script.txt"
    output = tmp_path / "review.json"
    script.write_text(SCRIPT)
    output.write_text("protected")
    cli = Path(__file__).resolve().parents[1] / "cinema_swarm.py"
    run = subprocess.run(
        [sys.executable, str(cli), "--extract-ontology", str(script),
         "--ontology-output", str(output)], cwd=tmp_path,
        capture_output=True, text=True, check=False,
    )
    assert run.returncode == 2
    assert output.read_text() == "protected"
