"""Actual media inspection and per-shot approved transformations."""
import hashlib
import json
import subprocess
import sys
import wave
from pathlib import Path

import pytest
from PIL import Image

from cinemaswarm_world import World, Character, Event
from cinemaswarm_world.identity import Identity, IdentityRegistry, Mutation
from cinemaswarm_world.embodiment import Body, BindingRegistry, BindingEvent
from cinemaswarm_world.media_evidence import load_evidence_plan, analyze_evidence

T0 = "2026-01-01T00:00:00Z"
T1 = "2026-01-02T00:00:00Z"


def fixture(tmp_path, transformed=False):
    world = World("sample", T0)
    world.instantiate(Character("mara", "Mara", T0))
    world.pulse(T1, [Event("e1", T1, "mara", "choice", detail="The coat changes", provenance="approved")])
    people = IdentityRegistry([Identity("mara", "Mara", T0, "id:face", "id:voice", "body-a")], T0)
    people.pulse(T1, [])
    binding = BindingRegistry([Body("body-a", "body:face", "body:voice", "red")], [], T0)
    binding.pulse(T1, [BindingEvent("coat", T1, "body_change", "body-a",
                                   {"clothing": "blue"}, "approved")] if transformed else [])
    body = binding.bodies["body-a"]
    manifest = {
        "version": 1, "world_id": "sample", "as_of": T1,
        "shots": [{"shot_id": "s1", "index": 0, "cast": [{
            "identity_id": "mara", "body_id": "body-a",
            "body_visual_anchor": body["visual_anchor"],
            "body_vocal_anchor": body["vocal_anchor"],
            "identity_voice_anchor": "id:voice", "clothing": body["clothing"],
            "visible_equipment": [], "voice_active": True,
        }]}]
    }
    for name, data in [("world.json", world.snapshot()), ("identity.json", people.snapshot()),
                       ("bindings.json", binding.snapshot()), ("manifest.json", manifest)]:
        (tmp_path / name).write_text(json.dumps(data))
    return {"shot_id": "s1", "at": T1, "world_snapshot": "world.json",
            "identity_snapshot": "identity.json", "asset_bindings": "bindings.json",
            "av_manifest": "manifest.json", "media": []}


def wav(path, data):
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(8000)
        from array import array
        out.writeframes(array("h", data).tobytes())


def test_identical_image_and_pcm_with_transformed_body(tmp_path):
    shot = fixture(tmp_path, transformed=True)
    Image.new("RGB", (12, 12), "blue").save(tmp_path / "reference.png")
    Image.new("RGB", (12, 12), "blue").save(tmp_path / "rendered.png")
    wav(tmp_path / "voice.wav", [100, -100] * 64)
    wav(tmp_path / "rendered.wav", [100, -100] * 64)
    shot["media"] = [
        {"identity_id": "mara", "kind": "image", "reference": "reference.png",
         "rendered": "rendered.png",
         "rendered_sha256": hashlib.sha256((tmp_path / "rendered.png").read_bytes()).hexdigest()},
        {"identity_id": "mara", "kind": "audio", "reference": "voice.wav",
         "rendered": "rendered.wav"},
    ]
    manifest_path = tmp_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["shots"][0]["cast"][0]["rendered_audio_sha256"] = hashlib.sha256(
        (tmp_path / "rendered.wav").read_bytes()
    ).hexdigest()
    manifest_path.write_text(json.dumps(manifest))
    plan = {"version": 1, "shots": [shot]}
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan))
    report = analyze_evidence(load_evidence_plan(path), tmp_path)
    assert report["status"] == "checks_passed"
    assert report["error_count"] == 0
    assert report["shots"][0]["metadata"]["status"] == "metadata_consistent"


def test_modified_pixels_and_audio_detected(tmp_path):
    shot = fixture(tmp_path)
    Image.new("RGB", (12, 12), "black").save(tmp_path / "a.png")
    Image.new("RGB", (12, 12), "white").save(tmp_path / "b.png")
    wav(tmp_path / "a.wav", [0] * 128)
    wav(tmp_path / "b.wav", [30000] * 128)
    shot["media"] = [
        {"identity_id": "mara", "kind": "image", "reference": "a.png", "rendered": "b.png"},
        {"identity_id": "mara", "kind": "audio", "reference": "a.wav", "rendered": "b.wav"},
    ]
    p = tmp_path / "plan.json"
    p.write_text(json.dumps({"version": 1, "shots": [shot]}))
    report = analyze_evidence(load_evidence_plan(p), tmp_path)
    assert report["status"] == "review_required"
    assert {x["field"] for x in report["findings"]} >= {"image_difference", "audio_difference"}


def test_image_misalignment_unknown_not_pass(tmp_path):
    shot = fixture(tmp_path)
    Image.new("RGB", (12, 12), "red").save(tmp_path / "a.png")
    Image.new("RGB", (6, 6), "red").save(tmp_path / "b.png")
    shot["media"] = [{"identity_id": "mara", "kind": "image",
                      "reference": "a.png", "rendered": "b.png"}]
    p = tmp_path / "plan.json"
    p.write_text(json.dumps({"version": 1, "shots": [shot]}))
    report = analyze_evidence(load_evidence_plan(p), tmp_path)
    assert report["status"] == "partial_evidence"
    assert report["unknown_count"] >= 1


def test_path_traversal_rejected(tmp_path):
    shot = fixture(tmp_path)
    shot["media"] = [{"identity_id": "mara", "kind": "image",
                      "reference": "../outside.png", "rendered": "../outside.png"}]
    p = tmp_path / "plan.json"
    p.write_text(json.dumps({"version": 1, "shots": [shot]}))
    with pytest.raises((ValueError, FileNotFoundError)):
        analyze_evidence(load_evidence_plan(p), tmp_path)


def test_rejects_backwards_time_and_untrusted_manifest(tmp_path):
    shot = fixture(tmp_path)
    shot["media"] = [{"identity_id": "mara", "kind": "image",
                      "reference": "a.png", "rendered": "b.png"}]
    p = tmp_path / "plan.json"
    p.write_text(json.dumps({"version": 1, "shots": [shot, {**shot, "shot_id": "s2", "at": T0}]}))
    with pytest.raises(ValueError):
        load_evidence_plan(p)


def test_cli_inspects_actual_files_offline(tmp_path):
    shot = fixture(tmp_path, transformed=True)
    Image.new("RGB", (6, 6), "blue").save(tmp_path / "a.png")
    Image.new("RGB", (6, 6), "blue").save(tmp_path / "b.png")
    shot["media"] = [{"identity_id": "mara", "kind": "image",
                      "reference": "a.png", "rendered": "b.png"}]
    manifest_path = tmp_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["shots"][0]["cast"][0]["voice_active"] = False
    manifest_path.write_text(json.dumps(manifest))
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"version": 1, "shots": [shot]}))
    cli = Path(__file__).resolve().parents[1] / "cinema_swarm.py"
    output = tmp_path / "report.json"
    call = subprocess.run([sys.executable, str(cli), "--analyze-media-evidence", str(plan),
                           "--media-root", str(tmp_path), "--media-report", str(output)],
                          capture_output=True, text=True, cwd=tmp_path)
    assert call.returncode == 0, call.stderr
    assert json.loads(output.read_text())["status"] == "checks_passed"


def test_two_shots_accept_separately_authorized_clothing_change(tmp_path):
    shot1 = fixture(tmp_path, transformed=False)
    Image.new("RGB", (4, 4), "red").save(tmp_path / "first.png")
    Image.new("RGB", (4, 4), "red").save(tmp_path / "first-render.png")
    shot1["media"] = [{"identity_id": "mara", "kind": "image",
                       "reference": "first.png", "rendered": "first-render.png"}]
    shot2 = fixture(tmp_path, transformed=True)
    for src, dest in (("world.json", "world-later.json"),
                      ("identity.json", "identity-later.json"),
                      ("bindings.json", "bindings-later.json"),
                      ("manifest.json", "manifest-later.json")):
        (tmp_path / src).replace(tmp_path / dest)
    shot1 = fixture(tmp_path, transformed=False)
    shot1["media"] = [{"identity_id": "mara", "kind": "image",
                       "reference": "first.png", "rendered": "first-render.png"}]
    from cinemaswarm_world.identity import IdentityRegistry
    from cinemaswarm_world.embodiment import BindingRegistry, BindingEvent
    reg = BindingRegistry.hydrate(json.loads((tmp_path / "bindings-later.json").read_text()))
    t2 = "2026-01-03T00:00:00Z"
    reg.pulse(t2, [BindingEvent("v2", t2, "body_change", "body-a",
                               {"clothing": "green"}, "approved")])
    (tmp_path / "bindings-later.json").write_text(reg.to_json())
    identities = IdentityRegistry.hydrate(json.loads((tmp_path / "identity-later.json").read_text()))
    identities.pulse(t2, [])
    (tmp_path / "identity-later.json").write_text(identities.to_json())
    later_world = json.loads((tmp_path / "world-later.json").read_text())
    later_world["time"] = t2
    (tmp_path / "world-later.json").write_text(json.dumps(later_world))
    manifest = json.loads((tmp_path / "manifest-later.json").read_text())
    manifest["as_of"] = t2
    manifest["shots"][0]["shot_id"] = "s2"
    manifest["shots"][0]["cast"][0]["clothing"] = "green"
    (tmp_path / "manifest-later.json").write_text(json.dumps(manifest))
    shot2.update({"shot_id": "s2", "at": t2, "world_snapshot": "world-later.json",
                  "identity_snapshot": "identity-later.json",
                  "asset_bindings": "bindings-later.json",
                  "av_manifest": "manifest-later.json"})
    Image.new("RGB", (4, 4), "green").save(tmp_path / "second.png")
    Image.new("RGB", (4, 4), "green").save(tmp_path / "second-render.png")
    shot2["media"] = [{"identity_id": "mara", "kind": "image",
                       "reference": "second.png", "rendered": "second-render.png"}]
    for name in ("manifest.json", "manifest-later.json"):
        doc = json.loads((tmp_path / name).read_text())
        doc["shots"][0]["cast"][0]["voice_active"] = False
        (tmp_path / name).write_text(json.dumps(doc))
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps({"version": 1, "shots": [shot1, shot2]}))
    report = analyze_evidence(load_evidence_plan(plan_path), tmp_path)
    assert report["status"] == "checks_passed"
    assert len(report["shots"]) == 2
    assert report["shots"][0]["metadata"]["status"] == "metadata_consistent"
    assert report["shots"][1]["metadata"]["status"] == "metadata_consistent"
