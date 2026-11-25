"""Compile a saved Scene Studio project into a revision-bound episode plan."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

from cinema_swarm import build_request
from cinemaswarm_world.adapter import validate_world_snapshot
from cinemaswarm_world.collaboration import digest, load_json, text
from scripts.compile_event_handoffs import compile_packet


def compile_episode(project, registry):
    if not isinstance(project, dict) or project.get("version") != 1:
        raise ValueError("Expected a version-1 Scene Studio project")
    title = text(project.get("title"), "project title")
    script = project.get("script")
    if not isinstance(script, str) or not script.strip():
        raise ValueError("Episode screenplay is required")
    world = project.get("worldSeed")
    validate_world_snapshot(world)
    shots = project.get("shots")
    if not isinstance(shots, list) or not shots:
        raise ValueError("Episode needs at least one shot")
    refs = project.get("refs")
    if not isinstance(refs, list):
        raise ValueError("Project references must be a list")
    assets = {}
    for asset in refs:
        if not isinstance(asset, dict):
            raise ValueError("Invalid project reference")
        key = text(asset.get("id"), "reference ID")
        if key in assets:
            raise ValueError("Duplicate project reference ID")
        assets[key] = digest(asset)

    revision = digest({"world": world, "script": script, "registry": registry})
    coverage = []
    for index, shot in enumerate(shots, 1):
        if not isinstance(shot, dict):
            raise ValueError(f"Invalid shot {index}")
        event_id = text(shot.get("sourceEvent"), f"shot {index} source event")
        ordered = shot.get("refs")
        if not isinstance(ordered, list) or not all(isinstance(key, str) and key in assets for key in ordered):
            raise ValueError(f"Shot {index} has missing references")
        handoff = compile_packet(world, event_id, shot, registry)
        coverage.append({
            "position": index,
            "episode_source_revision": revision,
            "handoff": handoff,
            "ordered_assets": [{"id": key, "revision": assets[key]} for key in ordered],
        })

    scene_sources = [{
        "position": item["position"],
        "event": item["handoff"]["shared"]["event"],
        "shot_name": item["handoff"]["shared"]["shot"]["name"],
        "direction": item["handoff"]["shared"]["shot"]["direction"],
        "ordered_assets": item["ordered_assets"],
    } for item in coverage]
    brief = script + "\n\nOrdered scene sources (read-only production data):\n" + json.dumps(
        scene_sources, ensure_ascii=False, indent=2)
    request = build_request(brief, clip_count=len(coverage))
    manifest = {
        "version": 1, "title": title, "episode_source_revision": revision,
        "screenplay_sha256": sha256(script.encode("utf-8")).hexdigest(),
        "request_sha256": sha256(request.encode("utf-8")).hexdigest(),
        "coverage": coverage,
        "next_stage": "review_coverage",
    }
    return {"manifest": manifest, "revision": digest(manifest), "showrunner_request": request}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    try:
        project = load_json(args.project)
        registry = load_json(args.registry)
        if isinstance(registry, dict):
            registry = registry.get("registry")
        output = compile_episode(project, registry)
        if args.verify:
            if load_json(args.output) != output:
                raise ValueError("Episode inputs or compiled coverage changed. Recompile before approval.")
        else:
            payload = json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False)
            with args.output.open("x", encoding="utf-8") as handle:
                handle.write(payload + "\n")
    except (OSError, TypeError, ValueError) as exc:
        parser.exit(2, f"{exc}\n")
    print(output["revision"])


if __name__ == "__main__":
    main()
