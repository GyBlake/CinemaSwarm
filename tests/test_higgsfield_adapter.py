"""Exercise the shot-contract to provider round trip without spending credits."""
import copy
from uuid import uuid4

import pytest

from cinemaswarm_world.higgsfield_adapter import (
    compile_plan, poll_shot, quote_shot, submit_shot,
)
from cinemaswarm_world.shot_execution import stage_handoffs
from tests.test_shot_execution import sample


def test_shared_asset_binding_and_render_receipt(tmp_path):
    package, semantics, symbols, graph, contract, _ = sample(tmp_path)
    handoff = stage_handoffs(contract, package, semantics, symbols, graph)
    first = handoff["shots"][0]
    later = copy.deepcopy(first)
    later.update(shot_id="later-shot", scene_id="later-scene")
    handoff["shots"].append(later)
    bindings = {
        ref["object_id"]: {"sha256": ref["sha256"], "role": "ref_element",
                           "value": str(uuid4())}
        for shot in handoff["shots"] for ref in shot["ordered_asset_refs"]
    }
    options = dict(model="test-model", aspect_ratio="16:9", resolution="720p")
    plan = compile_plan(handoff, bindings, **options)
    shot = plan["shots"][0]
    assert shot["params"]["medias"] == plan["shots"][-1]["params"]["medias"]
    assert shot["dialogue"][0]["voice_id"] == first["dialogue"][0]["voice_id"]
    first_asset = first["ordered_asset_refs"][0]["object_id"]
    bindings[first_asset]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="stale"):
        compile_plan(handoff, bindings, **options)

    submissions = []

    def higgsfield(operation, arguments):
        if operation == "estimate_video_cost":
            assert arguments["params"] == shot["params"]
            return {"cost": {"credits_exact": 4.5}, "quote_ref": "quote:one"}
        if operation == "generate_video":
            submissions.append(arguments)
            return {"results": [{"id": "job-one"}]}
        return {"jobs": [{"job_id": "job-one", "status": "completed",
                          "result_url": "https://example.com/clip.mp4"}]}

    quote = quote_shot(shot, higgsfield)
    with pytest.raises(ValueError, match="credit limit"):
        submit_shot(shot, quote, higgsfield, max_credits=4, ledger=tmp_path)
    receipt = submit_shot(shot, quote, higgsfield, max_credits=5, ledger=tmp_path)
    assert poll_shot(receipt, higgsfield)["status"] == "completed"
    with pytest.raises(ValueError, match="already claimed"):
        submit_shot(shot, quote, higgsfield, max_credits=5, ledger=tmp_path)
    assert submissions == [{"params": {"ref": "quote:one"}}]
