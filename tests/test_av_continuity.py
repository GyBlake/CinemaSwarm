"""Offline manifest-to-world audiovisual continuity contract regressions."""
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
from cinemaswarm_world import Character, Event, World
from cinemaswarm_world.identity import Identity, IdentityRegistry, Mutation
from cinemaswarm_world.embodiment import Body, Object, BindingRegistry, project_embodiment
from cinemaswarm_world.av_continuity import validate_av_continuity, check_media_hash

T0 = "2026-01-01T00:00:00Z"
T1 = "2026-01-02T00:00:00Z"


def setup(tmp_path=None, swap=False):
    world = World("lantern-city", T0)
    world.instantiate(Character("mara", "Mara", T0))
    world.instantiate(Character("kai", "Kai", T0))
    world.pulse(T1, [Event("scene-1", T1, "mara", "revelation", target_id="kai",
                           detail="Their bodies changed", provenance="approved")])
    people = IdentityRegistry([
        Identity("mara", "Mara", T0, "identity-visual:mara", "identity-voice:mara", "body-a"),
        Identity("kai", "Kai", T0, "identity-visual:kai", "identity-voice:kai", "body-b"),
    ], T0)
    people.pulse(T1, [Mutation("swap", T1, "mara", "body_swap",
                               {"with": "kai"}, "approved")] if swap else [])
    binding = BindingRegistry([
        Body("body-a", "image:body-a", "vocal:body-a", "red coat"),
        Body("body-b", "image:body-b", "vocal:body-b", "blue coat"),
    ], [Object("amulet", "asset:amulet", "intact", "worn", holder="body-a",
               slot="neck", owner="mara")], T0)
    binding.pulse(T1, [])
    projection = project_embodiment(people, binding)
    cast = []
    for pid, character in projection["characters"].items():
        cast.append({
            "identity_id": pid, "body_id": character["body_id"],
            "body_visual_anchor": character["body"]["visual_anchor"],
            "body_vocal_anchor": character["body"]["vocal_anchor"],
            "identity_voice_anchor": character["identity_voice_anchor"],
            "clothing": character["body"]["clothing"],
            "visible_equipment": sorted(character["worn"]),
            "voice_active": False,
        })
    manifest = {"version": 1, "world_id": "lantern-city", "as_of": T1,
                "shots": [{"shot_id": "s1", "index": 0, "cast": cast}]}
    if tmp_path:
        files = [tmp_path / n for n in ("world.json", "identity.json", "binding.json", "shots.json")]
        for path, data in zip(files, (world.snapshot(), people.snapshot(),
                                     binding.snapshot(), manifest)):
            path.write_text(json.dumps(data))
        return world, people, binding, manifest, files
    return world, people, binding, manifest


def test_matches_identity_and_body_swapped_equipment():
    world, people, assets, manifest = setup(swap=True)
    result = validate_av_continuity(manifest, world.snapshot(), people, assets)
    assert result["status"] == "metadata_consistent"
    mara = next(x for x in manifest["shots"][0]["cast"] if x["identity_id"] == "mara")
    kai = next(x for x in manifest["shots"][0]["cast"] if x["identity_id"] == "kai")
    assert mara["body_id"] == "body-b"
    assert mara["visible_equipment"] == []
    assert kai["visible_equipment"] == ["amulet"]


def test_flags_wrong_voice_body_and_equipment():
    world, people, assets, manifest = setup(swap=True)
    cast = manifest["shots"][0]["cast"]
    cast[0]["identity_voice_anchor"] = "voice:wrong"
    cast[0]["body_id"] = "body-a" if cast[0]["body_id"] == "body-b" else "body-b"
    cast[0]["visible_equipment"] = ["imaginary"]
    result = validate_av_continuity(manifest, world.snapshot(), people, assets)
    assert result["status"] == "metadata_mismatch"
    assert {"body_id", "identity_voice_anchor", "visible_equipment"} <= {
        f["field"] for f in result["findings"]}


def test_rejects_unsupported_or_duplicate_cast():
    world, people, assets, manifest = setup()
    manifest["shots"][0]["cast"].append(copy.deepcopy(manifest["shots"][0]["cast"][0]))
    with pytest.raises(ValueError, match="duplicate cast"):
        validate_av_continuity(manifest, world.snapshot(), people, assets)


def test_detects_unknown_audio_evidence_not_voice_mismatch():
    world, people, assets, manifest = setup()
    manifest["shots"][0]["cast"][0]["voice_active"] = True
    report = validate_av_continuity(manifest, world.snapshot(), people, assets)
    assert report["status"] == "metadata_consistent"
    assert any(x["severity"] == "unknown" for x in report["findings"])


def test_content_hash_integrity_only(tmp_path):
    media = tmp_path / "scene.bin"
    media.write_bytes(b"test rendered media")
    assert check_media_hash(media, hashlib.sha256(media.read_bytes()).hexdigest())
    assert not check_media_hash(media, "0" * 64)


def test_cli_validates_manifest_offline(tmp_path):
    _, _, _, _, files = setup(tmp_path)
    cli = Path(__file__).resolve().parents[1] / "cinema_swarm.py"
    output = tmp_path / "report.json"
    command = [sys.executable, str(cli), "--validate-av-manifest", str(files[3]),
               "--world-snapshot", str(files[0]), "--identity-snapshot", str(files[1]),
               "--asset-bindings", str(files[2]), "--av-report", str(output)]
    run = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    assert json.loads(output.read_text())["status"] == "metadata_consistent"
    assert not (tmp_path / "pilot_sequence.md").exists()


def test_cli_rejects_metadata_mismatch(tmp_path):
    _, _, _, manifest, files = setup(tmp_path)
    manifest["shots"][0]["cast"][0]["clothing"] = "wrong"
    files[3].write_text(json.dumps(manifest))
    cli = Path(__file__).resolve().parents[1] / "cinema_swarm.py"
    command = [sys.executable, str(cli), "--validate-av-manifest", str(files[3]),
               "--world-snapshot", str(files[0]), "--identity-snapshot", str(files[1]),
               "--asset-bindings", str(files[2]), "--av-report", str(tmp_path / "report.json")]
    run = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True)
    assert run.returncode == 3
    assert "metadata_mismatch" in run.stderr


def test_cli_requires_inputs(tmp_path):
    cli = Path(__file__).resolve().parents[1] / "cinema_swarm.py"
    r = subprocess.run([sys.executable, str(cli), "--validate-av-manifest", "missing.json"],
                       cwd=tmp_path, capture_output=True, text=True)
    assert r.returncode == 2
    assert "requires" in r.stderr
