"""Symbolic narrative: sign systems, story causality and fail-closed observed cues."""
import copy
import json
import subprocess
import sys
from pathlib import Path
import pytest

from cinemaswarm_world.collaboration import digest, load_json
from cinemaswarm_world.symbolic_narrative import (
    CHANNELS, OPS, validate_program, shot_directives, audit_symbolic,
)
from tests.gate_fixtures import write_gate


def sample(root):
    write_gate(root)
    return (
        load_json(root / "collaboration.json"),
        load_json(root / "symbolic.json"),
        load_json(root / "symbolic-observations.json"),
    )


def test_all_modalities_and_operators_have_explicit_contract():
    assert len(CHANNELS) == 12
    assert {"visual", "acoustic", "kinetic", "relational", "temporal",
            "numerical", "spatial", "linguistic", "material",
            "psychological", "cultural", "cinematic"} == CHANNELS
    assert {"plant","echo","mirror","invert","disguise","amplify","transmute",
            "converge","diverge","reveal","resolve"} == OPS


def test_handoff_persists_authored_meanings_and_misdirection(tmp_path):
    package, plan, evidence = sample(tmp_path)
    directions = shot_directives(plan, package)
    assert directions["symbolic_program_sha256"] == digest(plan)
    assert directions["directives"][0]["reveal_policy"] == "conceal"
    assert audit_symbolic(plan, package, evidence, tmp_path)["status"] == "checks_passed"


def test_visual_angel_foreshadow_and_delayed_reveal(tmp_path):
    package, plan, observations = sample(tmp_path)
    package["scenes"].append({"id": "later", "purpose": "Recognize the wing motif",
                              "visual_action": "The woman unfolds literal wings",
                              "start_ms": 2000, "end_ms": 4000})
    plan["package_sha256"] = digest(package)
    plan["beats"][0].update({"surface_explanation": "Two bodyguards create wing shadows",
                              "audience_knowledge": "The woman seems angelic",
                              "perceptual_directive": "Backlight the guards, reveal ordinary silhouettes",
                              "planned_payoff_episode": None})
    reveal = dict(plan["beats"][0], id="angel-reveal", scene_id="later",
                  start_ms=2100, end_ms=3200, operator="reveal",
                  depends_on="plant-trust", reveal_policy="reveal",
                  surface_explanation="Real feathers fill the room",
                  audience_knowledge="The woman is revealed as an angel")
    plan["beats"].append(reveal)
    assert validate_program(plan, package)
    wrong = copy.deepcopy(plan)
    wrong["beats"][1]["depends_on"] = None
    with pytest.raises(ValueError, match="predecessor"):
        validate_program(wrong, package)
    wrong = copy.deepcopy(plan)
    wrong["beats"][1]["reveal_policy"] = "conceal"
    with pytest.raises(ValueError, match="explicitly disclose"):
        validate_program(wrong, package)


def test_motif_cultural_meaning_is_not_universalized(tmp_path):
    package, plan, _ = sample(tmp_path)
    plan["motifs"][0]["cultural_source"] = "universal"
    with pytest.raises(ValueError, match="universal"):
        validate_program(plan, package)
    plan["motifs"][0]["cultural_source"] = "original screenplay"
    plan["motifs"][0]["numerical_pattern"] = {
       "count": 3, "arrangement": "Three guards in triangular formation",
       "narrative_function": "Triadic responsibility as an original story device"}
    assert validate_program(plan, package)


def test_unplanted_echo_and_chronology_are_forbidden(tmp_path):
    package, plan, _ = sample(tmp_path)
    plan["beats"][0]["operator"] = "echo"
    with pytest.raises(ValueError, match="seeded predecessor"):
        validate_program(plan, package)
    plan["beats"][0]["operator"] = "plant"
    plan["beats"][0]["end_ms"] = 2500
    with pytest.raises(ValueError, match="outside scene"):
        validate_program(plan, package)


def test_hidden_symbol_cannot_reveal_early(tmp_path):
    package, plan, _ = sample(tmp_path)
    plan["beats"][0]["reveal_policy"] = "reveal"
    with pytest.raises(ValueError, match="premature"):
        validate_program(plan, package)


def test_observed_evidence_missing_blocks_release(tmp_path):
    package, plan, evidence = sample(tmp_path)
    evidence["observations"] = []
    assert audit_symbolic(plan, package, evidence, tmp_path)["status"] == "incomplete"


def test_symbolic_drift_or_unapproved_review_blocks(tmp_path):
    package, plan, evidence = sample(tmp_path)
    evidence["observations"][0]["dramatic_intent_preserved"] = False
    report = audit_symbolic(plan, package, evidence, tmp_path)
    assert report["status"] == "blocked"
    assert any("dramatic_intent" in f for f in report["failures"])
    evidence["observations"][0]["dramatic_intent_preserved"] = True
    evidence["observations"][0]["reveal_policy_preserved"] = False
    assert audit_symbolic(plan, package, evidence, tmp_path)["status"] == "blocked"


def test_evidence_mutation_or_escape_blocked(tmp_path):
    package, plan, evidence = sample(tmp_path)
    (tmp_path / "voice.wav").write_bytes(b"tampered")
    result = audit_symbolic(plan, package, evidence, tmp_path)
    assert any("sha256_mismatch" in x for x in result["failures"])
    evidence["observations"][0]["evidence_path"] = "../outside.wav"
    result = audit_symbolic(plan, package, evidence, tmp_path)
    assert any("evidence_unavailable" in x for x in result["failures"])


def test_package_hash_must_match_production_identity(tmp_path):
    package, plan, _ = sample(tmp_path)
    plan["package_sha256"] = "0"*64
    with pytest.raises(ValueError, match="not bound"):
        validate_program(plan, package)


def test_cli_directives_and_review(tmp_path):
    package, plan, obs = sample(tmp_path)
    cli = Path(__file__).resolve().parents[1] / "cinema_swarm.py"
    for args in (
        ["--prepare-symbolic", str(tmp_path/"symbolic.json"),
         "--symbolic-package", str(tmp_path/"collaboration.json"),
         "--symbolic-output", str(tmp_path/"directives.json")],
        ["--audit-symbolic", str(tmp_path/"symbolic-observations.json"),
         "--symbolic-plan", str(tmp_path/"symbolic.json"),
         "--symbolic-package", str(tmp_path/"collaboration.json"),
         "--symbolic-root", str(tmp_path),
         "--symbolic-output", str(tmp_path/"inspected.json")],
    ):
        proc = subprocess.run([sys.executable, str(cli), *args],
                              text=True, capture_output=True, cwd=tmp_path)
        assert proc.returncode == 0, proc.stderr
    assert load_json(tmp_path/"inspected.json")["status"] == "checks_passed"


def test_candidate_and_season_disallow_symbolic_receipt_failure(tmp_path):
    from cinemaswarm_world.episode_renderer import validate_plan
    package, plan, obs = sample(tmp_path)
    candidate = {"version":1, "episode_id":"lantern-01", "profile":"smoke-vertical-v1",
       "mode":"candidate", "scenes":[{"scene_id":"opening","image_source":"frame.png",
       "duration_seconds":1,"approved":True,"continuity_report":"qc.json"}],
       "audio_source":"voice.wav","captions_source":"captions.srt",
       "collaboration_package":"collaboration.json","collaboration_ack":"ack.json",
       "performance_report":"performance.json"}
    with pytest.raises(ValueError, match="symbolic_program"):
        validate_plan(candidate)
