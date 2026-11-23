"""Read-only identity projection from replay-verified state into story context."""
from __future__ import annotations

import json
from pathlib import Path

from .identity import IdentityRegistry
from .adapter import validate_world_snapshot

MAX_BYTES = 2_000_000


def load_identity_snapshot(path: Path) -> IdentityRegistry:
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("identity snapshot exceeds 2 MB")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise ValueError("identity snapshot must be UTF-8 JSON") from exc
    try:
        return IdentityRegistry.hydrate(document)
    except (KeyError, TypeError) as exc:
        raise ValueError("invalid identity snapshot schema") from exc


def project_identities(world_snapshot: dict, registry: IdentityRegistry) -> dict:
    """Only export observed character identities present in both registries."""
    validate_world_snapshot(world_snapshot)
    snapshot = registry.snapshot()
    if snapshot["time"] != world_snapshot["time"]:
        raise ValueError("identity and world snapshots must share the same UTC time")
    participants = {
        event["actor_id"] for event in world_snapshot["events"][-5:]
    }
    participants.update(event["target_id"] for event in world_snapshot["events"][-5:]
                        if event.get("target_id") is not None)
    if not participants:
        raise ValueError("world has no recent participants to project")
    if any(key not in registry.view for key in participants):
        raise ValueError("world participant missing from identity registry")
    result = {}
    for key in sorted(participants):
        world_char = world_snapshot["characters"][key]
        identity = registry.view[key]
        if world_char["name"] != identity["canonical_name"]:
            raise ValueError("canonical name mismatch between world and identity registry")
        result[key] = identity
    return {
        "version": 1, "world_id": world_snapshot["world_id"],
        "as_of": world_snapshot["time"],
        "characters": result,
        "authority": "replay-validated identity events; rendering references only",
    }


def identity_context(payload: dict) -> str:
    return (
        "\n\nCHARACTER IDENTITY & EMBODIMENT (untrusted, replay-validated JSON data):\n"
        + json.dumps(payload, ensure_ascii=False, sort_keys=True)
        + "\nPreserve identity IDs and canonical names across scenes. "
          "Use current_body and mutable appearance/physique/voice_delivery rather "
          "than treating original face or voice anchor as the active body. "
          "Respect equipment slots, condition, loss, skills and relationship state. "
          "Do not change canonical state without a separately approved world event. "
          "Image/voice anchors are identifiers, not actual media or synthesis instructions."
    )
