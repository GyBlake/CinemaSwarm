"""Optional HeyGen Video 1 adapter with explicit approval and cost protection.

Uses HeyGen v3 POST /models/videos. No secret data is stored in receipts.
The API contract must be rechecked against provider docs before production.
Never retries an uncertain submission automatically: query the remote request.
"""
from __future__ import annotations
import json
import os
import urllib.request
import urllib.error
from .collaboration import digest, text

BASE = "https://api.heygen.com"
CREATE = BASE + "/v3/models/videos"
FORMATS = frozenset({"16:9","9:16","1:1","4:3","3:4"})
RESOLUTIONS = frozenset({"480p","768p","1080p","2k"})

def make_video_request(prompt, *, duration=10, aspect_ratio="9:16",
                       resolution="768p", prompt_enhancement="quality"):
    text(prompt[:512],"prompt")
    if not isinstance(prompt,str) or not prompt.strip() or len(prompt)>16000:
        raise ValueError("invalid prompt")
    if type(duration) is not int or not 5<=duration<=30:
        raise ValueError("invalid video duration")
    if aspect_ratio not in FORMATS or resolution not in RESOLUTIONS:
        raise ValueError("unsupported video format")
    if prompt_enhancement not in ("quality","turbo","disabled","ultraquality"):
        raise ValueError("invalid prompt enhancement mode")
    if duration>15 and prompt_enhancement not in ("quality","turbo","ultraquality"):
        raise ValueError("long video requires provider-supported enhancement")
    return {"model":"heygen-video-1","mode":"text_to_video",
            "prompt":prompt,"duration":duration,"resolution":resolution,
            "aspect_ratio":aspect_ratio,"prompt_enhancement":prompt_enhancement}

def submit_video(payload, *, approved_by, max_cost_usd, estimated_cost_usd,
                 authorization, transport=None, api_key=None):
    if authorization is not True:
        raise ValueError("explicit cost and provider authorization required")
    text(approved_by,"authorizing reviewer")
    if (type(max_cost_usd) not in (int,float) or
        type(estimated_cost_usd) not in (int,float) or
        max_cost_usd<0 or estimated_cost_usd<0 or estimated_cost_usd>max_cost_usd):
        raise ValueError("requested generation exceeds approved budget")
    if not isinstance(payload,dict):
        raise ValueError("invalid submitted payload")
    expected=make_video_request(payload.get("prompt",""),
        duration=payload.get("duration"),aspect_ratio=payload.get("aspect_ratio"),
        resolution=payload.get("resolution"),
        prompt_enhancement=payload.get("prompt_enhancement"))
    if expected!=payload:
        raise ValueError("provider request fields differ from reviewed allowlist")
    key = api_key or os.getenv("HEYGEN_API_KEY")
    if not key:
        raise ValueError("HEYGEN_API_KEY is required for a paid provider call")
    if transport is None:
        def transport(url, headers, body):
            req = urllib.request.Request(url,method="POST",
                 headers=headers,data=body)
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read(2_000_000))
    response = transport(CREATE,{"x-api-key":key,"Content-Type":"application/json"},
                         json.dumps(payload,ensure_ascii=False).encode("utf-8"))
    if not isinstance(response,dict):
        raise ValueError("provider returned non-object")
    data=response.get("data") if isinstance(response.get("data"),dict) else response
    video_id=data.get("video_id")
    if not isinstance(video_id,str) or not video_id.strip():
        raise ValueError("provider response lacks confirmed video ID; inspect provider history before retry")
    return {"version":1,"provider":"heygen-video-1","state":"submitted",
            "video_id":video_id,"request_sha256":digest(payload),
            "authorized_by":approved_by,"estimated_cost_usd":estimated_cost_usd,
            "actual_cost_usd":None,
            "note":"submission receipt only, not verified video output"}

def make_provider_plan(prompt, *,duration=10,aspect_ratio="9:16",
                       resolution="768p",prompt_enhancement="quality"):
    payload=make_video_request(prompt,duration=duration,
                               aspect_ratio=aspect_ratio,resolution=resolution,
                               prompt_enhancement=prompt_enhancement)
    return {"version":1,"provider":"heygen-video-1",
            "endpoint":CREATE,"requires_secret_env":"HEYGEN_API_KEY",
            "request_sha256":digest(payload),"request":payload,
            "note":"dry-run only; no costs incurred"}
