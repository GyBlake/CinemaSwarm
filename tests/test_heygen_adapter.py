"""Provider submission safety: dry-run, caps, SDK-independent transport."""
import copy
import json
import pytest
from cinemaswarm_world.heygen_adapter import (
    CREATE,make_video_request,make_provider_plan,submit_video)

def test_plan_without_network_or_key():
    plan=make_provider_plan("A woman crosses a threshold",duration=10)
    assert plan["provider"]=="heygen-video-1"
    assert plan["request"]["mode"]=="text_to_video"
    assert plan["endpoint"]==CREATE

def test_budget_and_authorization_fail_closed():
    payload=make_video_request("A woman enters a room")
    with pytest.raises(ValueError,match="authorization"):
        submit_video(payload,approved_by="editor",max_cost_usd=1,
                     estimated_cost_usd=0.5,authorization=False,api_key="test")
    with pytest.raises(ValueError,match="budget"):
        submit_video(payload,approved_by="editor",max_cost_usd=0.1,
                     estimated_cost_usd=0.5,authorization=True,api_key="test")

def test_allowlist_prevents_unreviewed_provider_options():
    payload=make_video_request("A woman enters a room")
    payload["unauthorized_setting"]="exfiltrate"
    with pytest.raises(ValueError,match="allowlist"):
        submit_video(payload,approved_by="editor",max_cost_usd=1,
                     estimated_cost_usd=0.5,authorization=True,api_key="test")

def test_transport_receipt_never_leaks_secret():
    payload=make_video_request("A woman enters a room")
    seen=[]
    def stub(url,headers,body):
        seen.append((url,headers,body))
        return {"data":{"video_id":"test-video-123"}}
    receipt=submit_video(payload,approved_by="editor",max_cost_usd=1,
                         estimated_cost_usd=0.5,authorization=True,
                         transport=stub,api_key="secret-token")
    assert receipt["video_id"]=="test-video-123"
    assert receipt["actual_cost_usd"] is None
    assert "secret-token" not in json.dumps(receipt)
    assert seen[0][1]["x-api-key"]=="secret-token"

def test_unacknowledged_submission_never_asserts_generation():
    payload=make_video_request("A woman enters a room")
    with pytest.raises(ValueError,match="confirmed video ID"):
        submit_video(payload,approved_by="editor",max_cost_usd=1,
                     estimated_cost_usd=0.5,authorization=True,
                     api_key="secret-token",
                     transport=lambda *a:{"data":{"status":"pending"}})
