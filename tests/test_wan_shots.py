"""Check the Wan workflow binding and ComfyUI job round trip."""
import copy

import pytest

from cinemaswarm_world.shot_execution import stage_handoffs
from scripts.wan_shots import plan_shot, status, submit
from tests.test_shot_execution import sample


def test_wan_workflow_binding_and_receipt(tmp_path):
    package, semantics, symbols, graph, contract, _ = sample(tmp_path)
    handoff = stage_handoffs(contract, package, semantics, symbols, graph)
    shot = handoff["shots"][0]
    workflow = {
        "1": {"class_type": "LoadImage", "inputs": {"image": "placeholder.png"}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": ""}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": ""}},
        "4": {"class_type": "WanImageToVideo", "inputs": {"length": 81}},
    }
    bindings = {"fps": 16, "image": ["1", "image"], "positive": ["2", "text"],
                "negative": ["3", "text"], "length": ["4", "length"]}
    frame = {"filename": "approved/wide.png", "references": shot["ordered_asset_refs"]}
    plan = plan_shot(handoff, shot["shot_id"], workflow, bindings, frame)
    inputs = plan["request"]["prompt"]
    assert inputs["1"]["inputs"]["image"] == frame["filename"]
    assert shot["camera"] in inputs["2"]["inputs"]["text"]
    assert inputs["4"]["inputs"]["length"] % 4 == 1
    assert workflow["1"]["inputs"]["image"] == "placeholder.png"
    assert plan["dialogue"] == shot["dialogue"]
    stale = copy.deepcopy(frame)
    stale["references"][0]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="references"):
        plan_shot(handoff, shot["shot_id"], workflow, bindings, stale)

    def comfy(url, payload):
        if url.endswith("/prompt"):
            assert payload == plan["request"]
            return {"prompt_id": "example-id"}
        assert url.endswith("/history/example-id")
        return {"example-id": {"status": {"status_str": "success", "completed": True},
                               "outputs": {"8": {"videos": [{"filename": "wide.mp4"}]}}}}

    server = "http://127.0.0.1:8188"
    receipt = submit(plan, server, tmp_path, comfy)
    assert status(receipt, comfy)["outputs"]["8"]["videos"][0]["filename"] == "wide.mp4"
    with pytest.raises(ValueError, match="already claimed"):
        submit(plan, server, tmp_path, comfy)
