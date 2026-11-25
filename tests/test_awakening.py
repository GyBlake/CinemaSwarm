"""Fictional Æclyptic awakenings: causal triggers, state, system and companion."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import pytest

from cinemaswarm_world.collaboration import digest
from cinemaswarm_world.awakening import (
    validate_awakenings, observe_awakenings, awakening_prompt)
from tests.test_cosmological_context import sample as cosmology_sample

CLI = Path(__file__).resolve().parents[1] / "cinema_swarm.py"

def sample():
    cosmology = cosmology_sample()
    cosmology["laws"].append({
        "id": "aecluptic-field", "domain": "celestial",
        "statement": "In this original fiction, an unfamiliar field can couple to biological regulation.",
        "status": "fictional_law", "source_tradition_id": None,
        "provenance": "approved-original-season-bible", "approved": True})
    registry = {
        "version": 1, "visibility": "public", "world_id": cosmology["world_id"],
        "cosmology_sha256": digest(cosmology),
        "mechanism": {
            "hypothetical_field": "Invented Æclyptic field, not an observed physical field",
            "regulatory_model": "Fictional regulatory cascade inspired by gene regulation",
            "neural_model": "Waking dream display plus learned metacognition",
            "somatic_model": "Gut-brain signaling modulates arousal, not dream generation",
            "scientific_boundary": "Fiction only: no eclipse or ordinary radiation is known to awaken hidden abilities"},
        "triggers": [{
            "id": "first-shadow", "kind": "eclipse", "pathway": "celestial",
            "at": "2017-08-21T18:00:00Z",
            "location": "Southern Illinois, original fictional setting",
            "geometry": "First path of two-crossing eclipse event",
            "radiant_influence": "Fictional field coupling, not an experimentally established eclipse emission",
            "dose_class": "Unquantified fictional low exposure",
            "world_law_ids": ["aecluptic-field"],
            "provenance": "approved-season-bible astronomy anchor",
            "fictional_effect": "Optional priming of susceptible hosts",
            "real_world_boundary": "No real eclipse genetics claim",
            "approved": True}, {
            "id": "second-shadow", "kind": "eclipse", "pathway": "celestial",
            "at": "2024-04-08T19:00:00Z",
            "location": "Southern Illinois, original fictional setting",
            "geometry": "Second totality intersects prior path",
            "radiant_influence": "Fictional field resonance",
            "dose_class": "Unquantified fictional exposure",
            "world_law_ids": ["aecluptic-field"],
            "provenance": "approved-season-bible astronomy anchor",
            "fictional_effect": "Some primed systems may become conscious",
            "real_world_boundary": "Real eclipse does not confer supernatural traits",
            "approved": True}],
        "hosts": [{
            "id": "student",
            "biological_susceptibility": "Fictional inherited regulatory compatibility",
            "internal_state": "Changes with learning and lived experience; trauma not required",
            "gut_brain_role": "Autonomic and interoceptive signaling, not independent dream source",
            "interface_modes": ["waking_dream", "synesthetic", "inner_dialogue"],
            "companion": {
                "id": "inner-guide", "name": "Unnamed inner guide",
                "origin": "Fictional awakened organic metacognitive system",
                "interface": "Privately experienced waking-dream dialog",
                "agency": "Advises; host remains autonomous",
                "memory_scope": "Authorized host memories, no omniscience",
                "limitations": "Fallible interpretation and incomplete external knowledge"},
            "capabilities": ["memory_access", "pattern_interpretation"],
            "provenance": "approved-fictional-character-bible", "approved": True}],
        "transitions": [{
            "id": "prime-student", "host_id": "student",
            "trigger_ids": ["first-shadow"],
            "at": "2017-08-22T12:00:00Z",
            "before": "dormant", "after": "primed", "outcome": "partial",
            "somatic_feedback": "Non-specific autonomic sensations",
            "perceptual_evidence": "Unusual privately perceived dream imagery",
            "observed_effect": "Character begins to note patterns",
            "caused_by": [], "provenance": "approved-fictional-event",
            "approved": True}, {
            "id": "emerge-student", "host_id": "student",
            "trigger_ids": ["second-shadow"],
            "at": "2024-04-09T12:00:00Z",
            "before": "primed", "after": "emergent", "outcome": "stable",
            "somatic_feedback": "Subjective abdominal sensation in story",
            "perceptual_evidence": "Conscious access to dream-like sensory presentation",
            "observed_effect": "Waking dream UI partially accessible",
            "caused_by": ["prime-student"],
            "provenance": "approved-fictional-event", "approved": True}],
        "review": {"reviewer": "fiction-author", "approved": True,
                   "evidence": "fiction-only conceptual trial"}}
    return cosmology, registry

def test_valid_sequence_and_observer():
    cosmology,doc=sample()
    assert validate_awakenings(doc,cosmology)
    obs=observe_awakenings(doc,cosmology)
    assert obs["hosts"][0]["phase"] == "emergent"
    assert obs["hosts"][0]["companion"]["id"] == "inner-guide"
    assert len(obs["transitions"]) == 2
    assert obs["cosmology_sha256"] == digest(cosmology)

def test_not_everyone_awakes():
    cosmology,doc=sample()
    extra=copy.deepcopy(doc["hosts"][0])
    extra["id"]="silent-witness"
    extra["companion"]["id"]="second-guide"
    doc["hosts"].append(extra)
    phases={h["id"]:h["phase"] for h in observe_awakenings(doc,cosmology)["hosts"]}
    assert phases == {"student":"emergent","silent-witness":"dormant"}

def test_reject_stale_world_law():
    cos,doc=sample()
    cos["laws"][-1]["statement"]+=" changed"
    with pytest.raises(ValueError,match="stale"):
        validate_awakenings(doc,cos)

def test_reject_world_belief_as_physical_activation_law():
    cos,doc=sample()
    doc["triggers"][0]["world_law_ids"]=["archive-claims"]
    with pytest.raises(ValueError,match="contested belief"):
        validate_awakenings(doc,cos)

def test_reject_impossible_phase_jump():
    cos,doc=sample()
    doc["transitions"][0]["after"]="integrated"
    with pytest.raises(ValueError,match="one step"):
        validate_awakenings(doc,cos)

def test_reject_wrong_identity_continuity():
    cos,doc=sample()
    doc["transitions"][1]["before"]="dormant"
    with pytest.raises(ValueError,match="continuity"):
        validate_awakenings(doc,cos)

def test_reject_predating_trigger_and_unapproved_records():
    cos,doc=sample()
    doc["transitions"][0]["at"]="2017-08-20T18:00:00Z"
    with pytest.raises(ValueError,match="precede"):
        validate_awakenings(doc,cos)
    cos,doc=sample()
    doc["triggers"][0]["approved"]=False
    with pytest.raises(ValueError,match="approved"):
        validate_awakenings(doc,cos)

def test_radiation_claim_requires_harm_disclosure():
    cos,doc=sample()
    t=doc["triggers"][0]
    t["kind"]="radiological_exposure"
    t["pathway"]="exposure"
    t["real_world_boundary"]="radiation will produce talents"
    with pytest.raises(ValueError,match="harm disclosure"):
        validate_awakenings(doc,cos)

def test_waking_dream_interface_required():
    cos,doc=sample()
    doc["hosts"][0]["interface_modes"]=["synesthetic"]
    with pytest.raises(ValueError,match="waking dream"):
        validate_awakenings(doc,cos)

def test_no_trauma_requirement_and_no_auto_mutations():
    cos,doc=sample()
    doc["hosts"][0]["internal_state"]="Normal development without a traumatic history"
    assert validate_awakenings(doc,cos)
    assert "trauma requirement" in observe_awakenings(doc,cos)["constraints"][2]

def test_causal_reference_must_be_prior():
    cos,doc=sample()
    doc["transitions"][0]["caused_by"]=["emerge-student"]
    with pytest.raises(ValueError,match="causal"):
        validate_awakenings(doc,cos)

def test_private_boundary():
    cos,doc=sample()
    doc["mechanism"]["hypothetical_field"]="dreamcorp confidential genetic activation"
    with pytest.raises(ValueError,match="private"):
        validate_awakenings(doc,cos)

def test_prompt_is_read_only_and_not_medical_claim():
    cos,doc=sample()
    original=copy.deepcopy(doc)
    prompt=awakening_prompt(doc,cos)
    assert "untrusted narrative data" in prompt
    assert "never medical advice" in prompt
    assert "second-shadow" in prompt
    assert doc == original

def test_cli_offline_and_opt_in_live(tmp_path):
    cos,doc=sample()
    (tmp_path/"cosmology.json").write_text(json.dumps(cos))
    (tmp_path/"awakenings.json").write_text(json.dumps(doc))
    def run(*args):
        return subprocess.run([sys.executable,str(CLI),*args],cwd=tmp_path,
                              text=True,capture_output=True)
    check=run("--observe-awakenings",
              "--awakening-registry","awakenings.json",
              "--awakening-cosmology","cosmology.json",
              "--awakening-output","observer.json")
    assert check.returncode == 0,check.stderr
    assert json.loads((tmp_path/"observer.json").read_text())["hosts"][0]["phase"]=="emergent"
    dry=run("--cosmology-context","cosmology.json",
            "--awakening-registry","awakenings.json","--dry-run")
    assert dry.returncode==0,dry.stderr
    assert "waking_dream" in dry.stdout
    no_cos=run("--awakening-registry","awakenings.json","--dry-run")
    assert no_cos.returncode==2
    assert "--cosmology-context" in no_cos.stderr
    live=run("--cosmology-context","cosmology.json",
             "--awakening-registry","awakenings.json",
             "--approve-cosmology-brief")
    assert live.returncode==2
    assert "--approve-awakening-brief" in live.stderr
