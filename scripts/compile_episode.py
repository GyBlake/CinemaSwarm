"""Compile a saved Scene Studio project into a revision-bound episode plan."""
import argparse
import asyncio
from hashlib import sha256
import json
import os
from pathlib import Path

from cinema_swarm import build_request, create_orchestrator, write_packet
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


def run_reviewed_episode(compiled, approved_revision, destination):
    """Submit the exact reviewed request to the existing specialist runtime once."""
    if approved_revision != compiled["revision"]:
        raise ValueError("Approval must match the current episode revision")
    if destination.exists():
        raise ValueError("Production output already exists")
    if not os.environ.get("OPENAI_API_KEY"):
        try:
            from dotenv import load_dotenv
        except ImportError:
            pass
        else:
            load_dotenv()
    if not os.environ.get("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY is required to run the CinemaSwarm specialists")
    from agents import Runner

    destination.parent.mkdir(parents=True, exist_ok=True)
    attempt = destination.with_name(destination.name + ".attempt.json")
    # Reserve the output before contacting the provider. Preserve the receipt on
    # exceptions so a lost response cannot trigger an automatic second run.
    with attempt.open("x", encoding="utf-8") as handle:
        json.dump({
            "revision": approved_revision,
            "request_sha256": compiled["manifest"]["request_sha256"],
            "output": destination.name,
        }, handle)
    result = asyncio.run(Runner.run(create_orchestrator(), compiled["showrunner_request"], max_turns=40))
    if not isinstance(result.final_output, str) or not result.final_output.strip():
        raise ValueError("Specialists returned no text production packet")
    write_packet(destination, result.final_output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--run-specialists", type=Path, metavar="PRODUCTION_PACKET",
                        help="Run the reviewed plan using the live model runtime")
    parser.add_argument("--approve-revision", help="Exact revision approved for provider processing")
    args = parser.parse_args()
    if args.run_specialists and not args.verify:
        parser.error("--run-specialists requires --verify against a saved plan")
    if bool(args.run_specialists) != bool(args.approve_revision):
        parser.error("--run-specialists and --approve-revision must be supplied together")

    try:
        project = load_json(args.project)
        registry = load_json(args.registry)
        if isinstance(registry, dict):
            registry = registry.get("registry")
        output = compile_episode(project, registry)
        if args.verify:
            if load_json(args.output) != output:
                raise ValueError("Episode inputs or compiled coverage changed. Recompile before approval.")
            if args.run_specialists:
                try:
                    run_reviewed_episode(output, args.approve_revision, args.run_specialists)
                except (OSError, ValueError):
                    raise
                except Exception as exc:
                    raise ValueError(
                        f"Specialist runtime failed ({type(exc).__name__}). Check the attempt state before retrying."
                    ) from exc
        else:
            payload = json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False)
            with args.output.open("x", encoding="utf-8") as handle:
                handle.write(payload + "\n")
    except (OSError, TypeError, ValueError) as exc:
        parser.exit(2, f"{exc}\n")
    print(output["revision"])


if __name__ == "__main__":
    main()
