"""Sanitized external collaboration contract, digest and author-approved acknowledgment.

No provider credentials, unapproved private canon or hidden reasoning is shared.
A provider acknowledgment is a signed-off production record, not an attestation
that a provider actually acquired MCP tools or internal state.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

MAX_BYTES = 2_000_000
CHANNELS = frozenset({"onscreen", "offscreen", "thought", "crowd", "disembodied"})
FIELDS = frozenset({"version", "project_id", "episode_id", "visibility", "creative_intent",
                    "canon", "characters", "relationships", "scenes", "dialogue", "provider"})
 
def text(value, name):
    if not isinstance(value, str) or not value.strip() or len(value) > 512:
        raise ValueError(f"invalid {name}")
    return value

def nonnegative(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(f"invalid {name}")
    return value

def digest(document):
    return hashlib.sha256(json.dumps(document, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()

def load_json(path: Path):
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("JSON contract too large")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid UTF-8 JSON contract") from exc

def validate_package(package):
    if not isinstance(package, dict) or set(package) != FIELDS or package["version"] != 1:
        raise ValueError("collaboration contract schema mismatch")
    for key in ("project_id", "episode_id", "creative_intent"):
        text(package[key], key)
    if package["visibility"] != "public":
        raise ValueError("external packages require explicit public visibility")
    canon = package["canon"]
    if not isinstance(canon, dict) or set(canon) != {"snapshot_id", "digest", "dramatic_beats"}:
        raise ValueError("invalid sanitized canon projection")
    text(canon["snapshot_id"], "canon snapshot")
    if not isinstance(canon["digest"], str) or len(canon["digest"]) != 64 or any(c not in "0123456789abcdef" for c in canon["digest"]):
        raise ValueError("invalid canonical SHA-256")
    beats = canon["dramatic_beats"]
    if not isinstance(beats, list) or not beats or len(beats) > 30:
        raise ValueError("canonical dramatic beats required")
    for beat in beats:
        text(beat, "dramatic beat")
    chars = package["characters"]
    if not isinstance(chars, list) or not 1 <= len(chars) <= 60:
        raise ValueError("character roster required")
    ids, voices = set(), set()
    for c in chars:
        if not isinstance(c, dict) or set(c) != {"id", "name", "visual_anchor", "voice_anchor", "voice_id",
                                                "voice_preview_sha256", "voice_approved"}:
            raise ValueError("character binding schema mismatch")
        for key in ("id", "name", "visual_anchor", "voice_anchor", "voice_id"):
            text(c[key], key)
        if c["id"] in ids or c["voice_id"] in voices:
            raise ValueError("character and voice IDs must be unique for distinct cast identities")
        ids.add(c["id"])
        voices.add(c["voice_id"])
        if not isinstance(c["voice_preview_sha256"], str) or len(c["voice_preview_sha256"]) != 64 or any(x not in "0123456789abcdef" for x in c["voice_preview_sha256"]):
            raise ValueError("voice preview SHA-256 required")
        if c["voice_approved"] is not True:
            raise ValueError("all character voice identities require approval")
    relations = package["relationships"]
    if not isinstance(relations, list) or len(relations) > 200:
        raise ValueError("relationships must be a bounded list")
    for relationship in relations:
        if not isinstance(relationship, dict) or set(relationship) != {"source", "target", "meaning"}:
            raise ValueError("relationship schema mismatch")
        if relationship["source"] not in ids or relationship["target"] not in ids:
            raise ValueError("relationship references unknown character")
        text(relationship["meaning"], "relationship meaning")
    scenes = package["scenes"]
    if not isinstance(scenes, list) or not 1 <= len(scenes) <= 120:
        raise ValueError("scene list required")
    scene_ids = set()
    for scene in scenes:
        if not isinstance(scene, dict) or set(scene) != {"id", "purpose", "visual_action", "start_ms", "end_ms"}:
            raise ValueError("scene schema mismatch")
        sid = text(scene["id"], "scene id")
        if sid in scene_ids:
            raise ValueError("duplicate scene id")
        scene_ids.add(sid)
        text(scene["purpose"], "dramatic purpose")
        text(scene["visual_action"], "show-dont-tell action")
        start, end = nonnegative(scene["start_ms"], "scene start"), nonnegative(scene["end_ms"], "scene end")
        if end <= start:
            raise ValueError("scene duration invalid")
    lines = package["dialogue"]
    if not isinstance(lines, list) or len(lines) > 600:
        raise ValueError("dialogue must be bounded")
    line_ids = set()
    for line in lines:
        if not isinstance(line, dict) or set(line) != {"id", "scene_id", "speaker_id", "channel", "voice_id",
                                                       "visible_character_id", "start_ms", "end_ms", "text"}:
            raise ValueError("dialogue schema mismatch")
        line_id = text(line["id"], "dialogue id")
        if line_id in line_ids:
            raise ValueError("duplicate dialogue id")
        line_ids.add(line_id)
        if line["scene_id"] not in scene_ids or line["speaker_id"] not in ids:
            raise ValueError("dialogue speaker or scene unknown")
        speaker = next(c for c in chars if c["id"] == line["speaker_id"])
        if line["voice_id"] != speaker["voice_id"]:
            raise ValueError("dialogue voice diverges from identity lock")
        if line["channel"] not in CHANNELS:
            raise ValueError("unsupported voice channel")
        visible = line["visible_character_id"]
        if line["channel"] == "onscreen":
            if visible != line["speaker_id"]:
                raise ValueError("onscreen dialogue must animate the speaking character")
        elif visible is not None:
            raise ValueError("offscreen/thought/crowd/disembodied speech must not animate a mouth")
        text(line["text"], "spoken dialogue")
        start, end = nonnegative(line["start_ms"], "dialogue start"), nonnegative(line["end_ms"], "dialogue end")
        scene = next(s for s in scenes if s["id"] == line["scene_id"])
        if not scene["start_ms"] <= start < end <= scene["end_ms"]:
            raise ValueError("dialogue timing outside scene")
    provider = package["provider"]
    if not isinstance(provider, dict) or set(provider) != {"name", "capabilities"}:
        raise ValueError("invalid provider declaration")
    text(provider["name"], "provider")
    capabilities = provider["capabilities"]
    if not isinstance(capabilities, dict) or set(capabilities) != {"structured_planning", "voice_binding",
                                                                 "per_character_lipsync", "mcp_resources"} or any(type(v) is not bool for v in capabilities.values()):
        raise ValueError("provider capability flags required")
    return package

def make_handoff(package):
    validate_package(package)
    return {"version": 1, "package_sha256": digest(package), "contract": package,
            "required_response": ["package_sha256", "provider", "understood_scene_ids",
                                  "understood_character_ids", "unknowns", "interpretation",
                                  "approved_by", "human_approved"]}

def validate_acknowledgment(package, ack):
    validate_package(package)
    if not isinstance(ack, dict) or set(ack) != {"package_sha256", "provider", "understood_scene_ids",
                                                 "understood_character_ids", "unknowns", "interpretation",
                                                 "approved_by", "human_approved"}:
        raise ValueError("invalid acknowledgment schema")
    if ack["package_sha256"] != digest(package) or ack["provider"] != package["provider"]["name"]:
        raise ValueError("acknowledgment does not match canonical handoff")
    if set(ack["understood_scene_ids"]) != {s["id"] for s in package["scenes"]}:
        raise ValueError("provider did not acknowledge every scene")
    if set(ack["understood_character_ids"]) != {c["id"] for c in package["characters"]}:
        raise ValueError("provider did not acknowledge every character")
    if ack["unknowns"] != []:
        raise ValueError("unresolved provider interpretation issues")
    text(ack["interpretation"], "interpretation")
    text(ack["approved_by"], "human reviewer")
    if ack["human_approved"] is not True:
        raise ValueError("interpretation needs human approval")
    return {"version": 1, "status": "checks_passed", "package_sha256": digest(package),
            "provider": ack["provider"], "approved_by": ack["approved_by"],
            "note": "local contract validation, not verification of a provider's internal cognition"}
