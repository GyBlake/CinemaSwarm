"""Translate validated CinemaSwarm shot handoffs into Higgsfield tool calls."""
from __future__ import annotations

import json
import math
from pathlib import Path
from uuid import UUID

from .collaboration import digest


def compile_plan(handoff, bindings, *, model, aspect_ratio, resolution):
    """Build ordered requests with one immutable provider binding per source asset."""
    if handoff.get("version") != 1 or not handoff.get("shot_contract_sha256"):
        raise ValueError("expected a CinemaSwarm --prepare-shots handoff")
    requests = []
    seen = set()
    for shot in handoff["shots"]:
        shot_id = shot["shot_id"]
        if shot_id in seen:
            raise ValueError(f"duplicate shot {shot_id}")
        seen.add(shot_id)
        length_ms = shot["end_ms"] - shot["start_ms"]
        duration = max(3, math.ceil(length_ms / 1000))
        if length_ms <= 0 or duration > 15:
            raise ValueError(f"{shot_id}: shot timing must be positive and no longer than 15 seconds")
        media = []
        start_frames = 0
        for reference in shot["ordered_asset_refs"]:
            asset = reference["object_id"]
            binding = bindings.get(asset)
            if not binding or binding.get("sha256") != reference["sha256"]:
                raise ValueError(f"{shot_id}: missing or stale Higgsfield binding for {asset}")
            role = binding["role"]
            if role not in {"image", "start_image", "end_image", "ref_element", "video", "audio"}:
                raise ValueError(f"{asset}: unsupported Higgsfield media role")
            start_frames += role == "start_image"
            media.append({"role": role, "value": str(UUID(binding["value"]))})
        if start_frames > 1:
            raise ValueError(f"{shot_id}: multiple start frames")
        semantics = shot["stage_semantics"]
        direction = {
            key: shot[key] for key in ("location", "camera", "blocking", "cast",
                                       "initial_state", "exit_state", "soundscape",
                                       "negative_constraints", "symbolic_directions")
        }
        direction["semantic_direction"] = semantics.get("video", semantics.get("image", {}))
        direction["audio_direction"] = (
            "Do not synthesize dialogue. Preserve the specified performance beats for separately "
            "recorded dialogue and approved voices at edit."
        )
        direction["dialogue"] = [
            {key: line[key] for key in ("speaker", "channel", "text")} for line in shot["dialogue"]
        ]
        params = {
            "model": model, "aspect_ratio": aspect_ratio, "resolution": resolution,
            "duration": duration, "count": 1, "medias": media,
            "prompt": "Render one continuous shot. Follow this shot contract:\n"
                      + json.dumps(direction, ensure_ascii=False, indent=2),
        }
        requests.append({
            "shot_id": shot_id, "scene_id": shot["scene_id"],
            "start_ms": shot["start_ms"], "end_ms": shot["end_ms"],
            "references": shot["ordered_asset_refs"], "dialogue": shot["dialogue"],
            "params": params, "request_sha256": digest(params),
        })
    if not requests:
        raise ValueError("shot handoff is empty")
    return {
        "version": 1, "episode_id": handoff["episode_id"],
        "shot_contract_sha256": handoff["shot_contract_sha256"], "shots": requests,
    }


def _call(tool, operation, arguments):
    response = tool(operation, arguments)
    if not isinstance(response, dict) or response.get("error"):
        raise ValueError(f"Higgsfield {operation}: {response}")
    return response


def quote_shot(shot, tool):
    params = shot["params"]
    if digest(params) != shot["request_sha256"]:
        raise ValueError("shot request changed after planning")
    result = _call(tool, "estimate_video_cost", {"params": params})
    if result.get("adjustments"):
        raise ValueError("provider adjusted render settings; revise the plan and quote again")
    cost = result.get("cost", {}).get("credits_exact")
    if type(cost) not in (int, float) or not math.isfinite(cost) or cost < 0:
        raise ValueError("provider did not return a valid credit quote")
    quote_ref = result.get("quote_ref")
    if not isinstance(quote_ref, str) or not quote_ref:
        raise ValueError("provider did not return a quote reference")
    return {
        "shot_id": shot["shot_id"], "request_sha256": shot["request_sha256"],
        "quote_ref": quote_ref, "credits": cost,
    }


def submit_shot(shot, quote, tool, *, max_credits, ledger):
    """Claim a request before calling the provider; ambiguous outcomes stay claimed."""
    if (quote["shot_id"] != shot["shot_id"]
            or quote["request_sha256"] != shot["request_sha256"]
            or digest(shot["params"]) != shot["request_sha256"]):
        raise ValueError("quote belongs to a different shot request")
    cost = quote["credits"]
    if any(type(value) not in (int, float) or not math.isfinite(value) or value < 0
           for value in (cost, max_credits)) or cost > max_credits:
        raise ValueError("quote exceeds approved credit limit")
    fresh = quote_shot(shot, tool)
    if fresh["credits"] > cost:
        raise ValueError("provider price increased; review a new quote")
    quote = fresh
    attempt = Path(ledger) / digest({"shot": shot["shot_id"], "request": shot["request_sha256"]})
    attempt.mkdir(parents=True, exist_ok=True)
    try:
        with (attempt / "submission.json").open("x", encoding="utf-8") as claim:
            json.dump(quote, claim)
    except FileExistsError:
        raise ValueError(f"shot request already claimed; reconcile provider history at {attempt}") from None
    result = _call(tool, "generate_video", {"params": {"ref": quote["quote_ref"]}})
    jobs = result.get("results", [])
    if len(jobs) != 1 or not jobs[0].get("id"):
        raise ValueError(f"no confirmed job ID; reconcile provider history at {attempt}")
    receipt = {**quote, "job_id": jobs[0]["id"]}
    (attempt / "job.json").write_text(json.dumps(receipt), encoding="utf-8")
    return receipt


def poll_shot(receipt, tool):
    result = _call(tool, "jobs_wait", {
        "jobs": [{"index": 0, "job_id": receipt["job_id"]}], "timeout_seconds": 0,
    })
    jobs = result.get("jobs", [])
    if len(jobs) != 1 or jobs[0].get("job_id") != receipt["job_id"]:
        raise ValueError("provider status did not match the shot receipt")
    return {**receipt, "status": jobs[0]["status"], "media_url": jobs[0].get("result_url")}
