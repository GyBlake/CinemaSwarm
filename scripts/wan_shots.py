"""Compile CinemaSwarm shots for a trusted Wan ComfyUI workflow and track jobs."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path, PurePosixPath
from urllib.parse import quote
from urllib.request import Request, urlopen

from cinemaswarm_world.collaboration import digest


def plan_shot(handoff, shot_id, workflow, config, frame):
    if handoff.get("version") != 1 or not handoff.get("shot_contract_sha256"):
        raise ValueError("expected a CinemaSwarm --prepare-shots handoff")
    shots = [shot for shot in handoff["shots"] if shot["shot_id"] == shot_id]
    if len(shots) != 1:
        raise ValueError(f"expected one shot named {shot_id}")
    shot = shots[0]
    if frame["references"] != shot["ordered_asset_refs"]:
        raise ValueError("approved first frame references do not match the shot")
    filename = frame["filename"]
    if (not filename or filename.startswith("/") or ".." in PurePosixPath(filename).parts
            or "\\" in filename):
        raise ValueError("first frame must name an uploaded ComfyUI input image")
    if not workflow or not all(isinstance(node, dict) and "class_type" in node
                               and isinstance(node.get("inputs"), dict)
                               for node in workflow.values()):
        raise ValueError("export the workflow in ComfyUI API format")
    fps = config["fps"]
    duration = shot["end_ms"] - shot["start_ms"]
    if type(fps) is not int or fps < 1 or duration < 1:
        raise ValueError("positive FPS and shot duration required")
    frames = 1 + 4 * ((duration * fps + 3999) // 4000)
    positive = {key: shot[key] for key in (
        "location", "camera", "blocking", "initial_state", "exit_state", "symbolic_directions"
    )}
    semantics = shot["stage_semantics"]
    positive["semantics"] = semantics.get("video", semantics.get("image", {}))
    values = {
        "image": filename,
        "positive": "One continuous shot. " + json.dumps(positive, ensure_ascii=False),
        "negative": "; ".join(shot["negative_constraints"]),
        "length": frames,
    }
    graph = copy.deepcopy(workflow)
    targets = [(node, field) for node, field in (config[key] for key in values)]
    if len(set(targets)) != len(targets):
        raise ValueError("each workflow binding must target a distinct input")
    for (node, field), value in zip(targets, values.values()):
        if node not in graph or field not in graph[node]["inputs"]:
            raise ValueError(f"workflow input missing: {node}.{field}")
        if isinstance(graph[node]["inputs"][field], list):
            raise ValueError(f"workflow input is a connection: {node}.{field}")
        graph[node]["inputs"][field] = value
    return {
        "shot_id": shot_id, "episode_id": handoff["episode_id"],
        "contract_sha256": handoff["shot_contract_sha256"],
        "frame": frame, "direction": shot["blocking"], "dialogue": shot["dialogue"],
        "start_ms": shot["start_ms"],
        "end_ms": shot["end_ms"], "workflow_sha256": digest(workflow),
        "request": {"prompt": graph}, "request_sha256": digest({"prompt": graph}),
    }


def submit(plan, server, ledger, transport):
    request = plan["request"]
    if digest(request) != plan["request_sha256"]:
        raise ValueError("workflow request changed after preparation")
    directory = Path(ledger) / digest({
        "shot": plan["shot_id"], "episode": plan["episode_id"],
        "request": plan["request_sha256"], "server": server,
    })
    directory.mkdir(parents=True, exist_ok=True)
    try:
        with (directory / "submission.json").open("x", encoding="utf-8") as claim:
            json.dump(plan, claim)
    except FileExistsError:
        raise ValueError(f"request already claimed; reconcile the ComfyUI queue at {directory}") from None
    result = transport(server + "/prompt", request)
    if not result.get("prompt_id"):
        raise ValueError(f"no ComfyUI prompt ID; inspect the queue before retrying: {directory}")
    receipt = {
        "server": server, "prompt_id": result["prompt_id"], "shot_id": plan["shot_id"],
        "episode_id": plan["episode_id"], "request_sha256": plan["request_sha256"],
    }
    (directory / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
    return receipt


def status(receipt, transport):
    prompt_id = receipt["prompt_id"]
    result = transport(receipt["server"] + "/history/" + quote(prompt_id, safe=""), None)
    entry = result.get(prompt_id)
    if entry is None:
        return {**receipt, "state": "not_in_history"}
    state = entry.get("status", {})
    return {**receipt, "state": state.get("status_str", "unknown"),
            "completed": state.get("completed", False), "outputs": entry.get("outputs", {})}


def http_json(url, data):
    body = json.dumps(data).encode("utf-8") if data is not None else None
    request = Request(url, data=body, headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    planning = commands.add_parser("plan")
    for name in ("handoff", "shot", "workflow", "bindings", "frame"):
        planning.add_argument(name)
    submission = commands.add_parser("submit")
    submission.add_argument("plan")
    submission.add_argument("--server", default="http://127.0.0.1:8188")
    submission.add_argument("--ledger", required=True)
    commands.add_parser("status").add_argument("receipt")
    args = parser.parse_args()
    try:
        if args.command == "plan":
            output = plan_shot(read(args.handoff), args.shot, read(args.workflow),
                               read(args.bindings), read(args.frame))
        elif args.command == "submit":
            output = submit(read(args.plan), args.server.rstrip("/"), args.ledger, http_json)
        else:
            output = status(read(args.receipt), http_json)
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(1, f"{exc}\n")
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
