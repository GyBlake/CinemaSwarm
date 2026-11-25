"""Bind a selected world event, shot and department registry into one packet."""
import argparse
import json
from pathlib import Path

from cinemaswarm_world.adapter import load_world_snapshot
from cinemaswarm_world.collaboration import digest, load_json, text


def compile_packet(world, event_id, shot, registry):
    event = next((event for event in world["events"] if event["id"] == event_id), None)
    if event is None:
        raise ValueError("Selected event is absent from the world ledger")
    if not isinstance(shot, dict) or shot.get("sourceEvent") != event_id:
        raise ValueError("Shot must link to the selected world event")
    text(shot.get("name"), "shot name")
    if not isinstance(shot.get("direction"), str) or not shot["direction"].strip():
        raise ValueError("Shot direction is required")
    if not isinstance(registry, list) or not registry:
        raise ValueError("A department registry is required")

    shared = {
        "world_id": world["world_id"], "world_revision": digest(world),
        "event": event, "event_revision": digest(event),
        "shot": shot, "shot_revision": digest(shot), "registry_revision": digest(registry),
    }
    revision = digest(shared)
    packets = []
    ids = set()
    for department in registry:
        if not isinstance(department, dict):
            raise ValueError("Invalid department")
        key = text(department.get("id"), "department ID")
        if key in ids:
            raise ValueError("Duplicate department ID")
        ids.add(key)
        packets.append({
            "department": key, "source_revision": revision,
            "assignment": text(department.get("mission"), "department mission"),
            "expected_output": text(department.get("output"), "department output"),
            "review_gate": text(department.get("approval_gate"), "review gate"),
            "status": "prepared",
        })
    return {"version": 1, "shared": shared, "source_revision": revision,
            "departments": packets, "status": "planning_only"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--world", type=Path, required=True)
    parser.add_argument("--event", required=True)
    parser.add_argument("--shot", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    try:
        registry = load_json(args.registry)
        if isinstance(registry, dict):
            registry = registry.get("registry")
        packet = compile_packet(load_world_snapshot(args.world), args.event, load_json(args.shot), registry)
        if args.verify:
            if load_json(args.output) != packet:
                raise ValueError("Stale or modified handoff. Recompile from the current inputs.")
        else:
            payload = json.dumps(packet, ensure_ascii=False, indent=2, allow_nan=False)
            with args.output.open("x", encoding="utf-8") as handle:
                handle.write(payload + "\n")
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(2, f"{exc}\n")
    print(f"{len(packet['departments'])} department handoffs: {packet['source_revision']}")


if __name__ == "__main__":
    main()
