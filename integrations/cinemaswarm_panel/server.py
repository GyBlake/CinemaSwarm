"""Serve the CinemaSwarm MCP panel from a single trusted production workspace."""
from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlencode, urlsplit

from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, TextContent, ToolAnnotations

from cinemaswarm_world.collaboration import digest
from scripts.wan_shots import http_json, read, status, submit

RESOURCE = "ui://cinemaswarm/production.html"
HTML = Path(__file__).with_name("panel.html")
DEMO = (
    {"shot_id": "EG-01", "label": "Gate wide", "direction": "Establish the near bank and the flooded threshold."},
    {"shot_id": "EG-04", "label": "Reverse reveal", "direction": "Hold the gate geography as the second figure walks away."},
)


def create_app(root, comfy=None, transport=http_json, port=8000):
    root = Path(root)
    ledger = root / "renders"
    server = FastMCP("CinemaSwarm", host="127.0.0.1", port=port, stateless_http=True, json_response=True)
    comfy = comfy.rstrip("/") if comfy else None
    parsed = urlsplit(comfy or "")
    origin = f"{parsed.scheme}://{parsed.netloc}"
    https = parsed.scheme == "https"

    def get_plans():
        directory = root / "plans"
        plans = {}
        for path in sorted(directory.glob("*.json")):
            plan = read(path)
            if digest(plan["request"]) != plan["request_sha256"]:
                raise ValueError(f"Edited render request: {path.name}")
            key = digest(plan)
            plans[key] = plan
        return plans

    def preview_for(plan):
        preview = plan.get("preview")
        if isinstance(preview, str) and preview.startswith(
            ("data:image/png;base64,", "data:image/jpeg;base64,", "data:image/webp;base64,")
        ):
            return preview
        return None

    def state(key, plan):
        approval = root / "approvals" / key
        shot = {
            "key": key, "shot_id": plan["shot_id"], "label": plan["shot_id"],
            "direction": plan.get("direction", ""), "frame": plan["frame"]["filename"],
            "references": plan["frame"]["references"], "approved": approval.is_file(),
            "preview": preview_for(plan),
        }
        if not comfy:
            return {**shot, "state": "Awaiting ComfyUI"}
        attempt = ledger / digest({
            "shot": plan["shot_id"], "episode": plan["episode_id"],
            "request": plan["request_sha256"], "server": comfy,
        })
        receipt_path = attempt / "receipt.json"
        if not receipt_path.is_file():
            return {**shot, "state": "Needs reconciliation" if attempt.exists() else "Ready to queue"}
        shot["state"] = "Queued"
        try:
            result = status(read(receipt_path), transport)
        except OSError:
            return {**shot, "state": "Status unavailable"}
        shot["state"] = {"not_in_history": "Queued", "success": "Rendered",
                         "error": "Failed"}.get(result["state"], result["state"])
        if result.get("completed") and https:
            for node in result["outputs"].values():
                for items in node.values():
                    if not isinstance(items, list):
                        continue
                    for item in items:
                        filename = item.get("filename", "") if isinstance(item, dict) else ""
                        if filename.lower().endswith((".mp4", ".webm")):
                            params = {"filename": filename, "type": item.get("type", "output"),
                                      "subfolder": item.get("subfolder", "")}
                            return {**shot, "video": comfy + "/view?" + urlencode(params)}
        return shot

    def snapshot():
        plans = get_plans()
        shots = [state(key, plan) for key, plan in plans.items()]
        return {"demo": not shots, "connected": bool(comfy), "shots": shots or list(DEMO)}

    @server.resource(RESOURCE, mime_type="text/html;profile=mcp-app",
                     meta={"ui": {"csp": {"resourceDomains": [origin] if https else []}}})
    def panel() -> str:
        return HTML.read_text(encoding="utf-8")

    def reply():
        data = snapshot()
        previews = {shot["key"]: shot.pop("preview") for shot in data["shots"] if shot.get("preview")}
        return CallToolResult(content=[TextContent(type="text", text="CinemaSwarm shot board")],
                              structuredContent=data, _meta={"previews": previews})

    @server.tool(meta={"ui": {"resourceUri": RESOURCE}},
                 annotations=ToolAnnotations(readOnlyHint=True))
    def open_production() -> CallToolResult:
        """Open CinemaSwarm and show current shot references and render status."""
        return reply()

    ui_only = {"ui": {"visibility": ["app"]}}

    @server.tool(meta=ui_only, annotations=ToolAnnotations(destructiveHint=False))
    def approve_frame(key: str) -> CallToolResult:
        """Approve the displayed first frame for this exact render plan."""
        plan = get_plans().get(key)
        if plan is None:
            raise ValueError("Shot changed. Refresh before approving.")
        if not preview_for(plan):
            raise ValueError("Attach the first-frame preview before approving.")
        approvals = root / "approvals"
        approvals.mkdir(parents=True, exist_ok=True)
        (approvals / key).touch()
        return reply()

    @server.tool(meta=ui_only, annotations=ToolAnnotations(destructiveHint=False))
    def queue_render(key: str) -> CallToolResult:
        """Queue one approved shot on the configured ComfyUI server."""
        plan = get_plans().get(key)
        if plan is None or not (root / "approvals" / key).is_file():
            raise ValueError("Approve the current first frame before queuing.")
        if not comfy:
            raise ValueError("ComfyUI is not configured.")
        submit(plan, comfy, ledger, transport)
        return reply()

    return server


if __name__ == "__main__":
    create_app(os.getenv("CINEMASWARM_WORKSPACE", "private/panel"),
               os.getenv("COMFYUI_URL"),
               port=int(os.getenv("CINEMASWARM_PORT", "8000"))).run(transport="streamable-http")
