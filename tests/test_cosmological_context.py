"""Cosmological world-first context: cultural provenance, ambient archetypes, causal events."""
import copy
import json
import subprocess
import sys
from pathlib import Path
import pytest
from cinemaswarm_world.cosmological_context import (
    validate_cosmology,observer,prompt_context)
from cinemaswarm_world import World,Character,Event

CLI=Path(__file__).resolve().parents[1]/"cinema_swarm.py"

def sample():
    return {
        "version":1,"visibility":"public","world_id":"mythic-archipelago",
        "premise":"An archipelago of schools interpreting the same recurring dream.",
        "traditions":[
            {"id":"original-dreamers","name":"Dream Navigation Guild",
             "cultural_context":"original invented fiction, not a real tradition",
             "source_type":"original_fiction",
             "source_reference":"approved-original-world-bible",
             "scope":"fiction-only",
             "interpretation":"Dreams are maps under the fictional world's physics.",
             "reviewer":"world-author","approved":True},
            {"id":"original-archives","name":"Civic Archive",
             "cultural_context":"original invented fiction, not a real tradition",
             "source_type":"original_fiction",
             "source_reference":"approved-original-world-bible",
             "scope":"fiction-only",
             "interpretation":"Dreams are mnemonic fragments, not literal routes.",
             "reviewer":"world-author","approved":True}],
        "laws":[
            {"id":"dreams-can-map","domain":"dream","statement":"Dreams can encode pathways.",
             "status":"fictional_law","source_tradition_id":None,
             "provenance":"approved-original-world-bible","approved":True},
            {"id":"archive-claims","domain":"informational",
             "statement":"Archive members believe dreams are memories only.",
             "status":"in_world_belief","source_tradition_id":"original-archives",
             "provenance":"archive-charter-in-fiction","approved":True}],
        "archetypes":[
            {"id":"interpreter","label":"Interpreter","function":"Translate uncertain experiences",
             "tradition_ids":["original-dreamers"],
             "source_refs":["approved-original-world-bible"],
             "ambient":True,
             "interpretation":"Potential occupation, not an assigned protagonist.",
             "approved":True},
            {"id":"archivist","label":"Custodian of records",
             "function":"Safeguard institutional memory",
             "tradition_ids":["original-archives"],
             "source_refs":["approved-original-world-bible"],
             "ambient":True,"interpretation":"Not necessarily an antagonist",
             "approved":True}],
        "mappings":[
            {"id":"interpretation-bridge","left_archetype_id":"interpreter",
             "right_archetype_id":"archivist","relation":"functional_overlap",
             "shared_function":"Both interpret records",
             "differences":"One navigates dreams, one safeguards documents",
             "source_refs":["approved-original-world-bible"],
             "reviewed_by":"world-author","approved":True}],
        "institutions":[
            {"id":"academy","name":"Dream Academy",
             "framework":"Dreams are locations",
             "law_ids":["dreams-can-map"],"archetype_ids":[],
             "beliefs":"Navigation can be taught",
             "provenance":"approved-original-world-bible","approved":True},
            {"id":"archive","name":"Record Library",
             "framework":"Dreams are memories",
             "law_ids":["archive-claims"],"archetype_ids":["archivist"],
             "beliefs":"Records are conserved",
             "provenance":"approved-original-world-bible","approved":True}],
        "events":[
            {"id":"record1","timestamp":"2026-01-02T08:00:00Z",
             "actor_id":"student","kind":"discovery",
             "law_ids":["dreams-can-map"],
             "institution_ids":["academy","archive"],
             "caused_by":[],
             "consequence":"A map fragment challenges both institutions",
             "provenance":"approved-episode-ledger","approved":True},
            {"id":"record2","timestamp":"2026-01-03T08:00:00Z",
             "actor_id":"student","kind":"investigation",
             "law_ids":["dreams-can-map","archive-claims"],
             "institution_ids":["academy","archive"],
             "caused_by":["record1"],
             "consequence":"The student finds an archival contradiction",
             "provenance":"approved-episode-ledger","approved":True}],
        "governance":{"reviewer":"world-author","approved":True,
                      "evidence":"author-approved-original-fiction"}}

def test_valid_world_and_observer_do_not_assign_archetypes():
    doc=sample()
    assert validate_cosmology(doc)
    obs=observer(doc)
    assert [x["event_id"] for x in obs["narrative_seeds"]]==["record1","record2"]
    assert [x["id"] for x in obs["ambient_archetype_catalog"]]==["interpreter","archivist"]
    assert "archetype_id" not in obs["narrative_seeds"][0]
    assert "functional_overlap" not in obs["constraints"][1]

def test_in_world_belief_is_not_rewritten_as_physics():
    obs=observer(sample())
    laws=obs["narrative_seeds"][1]["applicable_laws"]
    assert {l["id"]:l["status"] for l in laws}=={
        "dreams-can-map":"fictional_law",
        "archive-claims":"in_world_belief"}

def test_mappings_preserve_difference_and_disallow_identity_equivalence():
    doc=sample()
    doc["mappings"][0]["relation"]="equivalent"
    with pytest.raises(ValueError,match="unsupported cross-cultural"):
        validate_cosmology(doc)
    doc=sample()
    doc["mappings"][0]["differences"]=""
    with pytest.raises(ValueError,match="differences"):
        validate_cosmology(doc)

def test_historical_claims_require_named_references():
    doc=sample()
    doc["traditions"][0]["source_type"]="primary_text"
    with pytest.raises(ValueError,match="identifiable"):
        validate_cosmology(doc)

def test_sources_cannot_be_unapproved():
    doc=sample()
    doc["traditions"][0]["approved"]=False
    with pytest.raises(ValueError,match="authorization"):
        validate_cosmology(doc)

def test_no_made_up_future_causal_event():
    doc=sample()
    doc["events"][1]["caused_by"]=["missing-prior-event"]
    with pytest.raises(ValueError,match="unknown event causes"):
        validate_cosmology(doc)
    doc=sample()
    doc["events"][0]["caused_by"]=["record2"]
    with pytest.raises(ValueError,match="unknown event causes"):
        validate_cosmology(doc)

def test_events_have_approved_order_and_utc():
    doc=sample()
    doc["events"][1]["timestamp"]="2026-01-01T08:00:00Z"
    with pytest.raises(ValueError,match="chronological"):
        validate_cosmology(doc)
    doc=sample()
    doc["events"][0]["timestamp"]="2026-01-02T08:00:00"
    with pytest.raises(ValueError,match="UTC"):
        validate_cosmology(doc)

def test_archetypes_remain_ambient_not_compulsory():
    doc=sample()
    doc["archetypes"][0]["ambient"]=False
    assert observer(doc)["ambient_archetype_catalog"]==[
        {"id":"archivist","function":"Safeguard institutional memory",
         "traditions":["original-archives"]}]

def test_no_private_context_in_public_contract():
    doc=sample()
    doc["premise"]="dreamcorp private canon"
    with pytest.raises(ValueError,match="private"):
        validate_cosmology(doc)

def test_no_mutation_and_prompt_separates_untrusted_context():
    doc=sample()
    original=copy.deepcopy(doc)
    result=prompt_context(doc)
    assert "untrusted story data" in result
    assert "archive-claims" in result
    assert doc==original

def test_cli_observer_and_world_first_dry_run(tmp_path):
    doc=sample()
    (tmp_path/"cosmology.json").write_text(json.dumps(doc))
    def run(*flags):
        return subprocess.run([sys.executable,str(CLI),*flags],
            cwd=tmp_path,text=True,capture_output=True)
    observe=run("--observe-cosmology","cosmology.json",
                "--cosmology-output","seeds.json")
    assert observe.returncode==0,observe.stderr
    assert json.loads((tmp_path/"seeds.json").read_text())["world_id"]==doc["world_id"]
    planned=run("--cosmology-context","cosmology.json","--dry-run")
    assert planned.returncode==0,planned.stderr
    assert "cosmological context" in planned.stdout.lower()
    live=run("--cosmology-context","cosmology.json")
    assert live.returncode==2
    assert "--approve-cosmology-brief" in live.stderr

def test_optional_world_binding_requires_committed_event(tmp_path):
    doc=sample()
    (tmp_path/"cosmology.json").write_text(json.dumps(doc))
    world=World("mythic-archipelago","2026-01-01T00:00:00Z")
    world.instantiate(Character("student","Student","2026-01-01T00:00:00Z"))
    world.pulse("2026-01-02T08:00:00Z",[
        Event("record1","2026-01-02T08:00:00Z","student","revelation",
              detail="A map fragment challenges both institutions",
              provenance="approved-episode-ledger")])
    (tmp_path/"world.json").write_text(world.to_json())
    command=[sys.executable,str(CLI),"--cosmology-context","cosmology.json",
             "--world-snapshot","world.json","--dry-run"]
    run=subprocess.run(command,cwd=tmp_path,capture_output=True,text=True)
    assert run.returncode==2
    assert "not committed" in run.stderr
    world.pulse("2026-01-03T08:00:00Z",[
        Event("record2","2026-01-03T08:00:00Z","student","revelation",
              detail="The student finds an archival contradiction",
              provenance="approved-episode-ledger")])
    (tmp_path/"world.json").write_text(world.to_json())
    run=subprocess.run(command,cwd=tmp_path,capture_output=True,text=True)
    assert run.returncode==0,run.stderr
