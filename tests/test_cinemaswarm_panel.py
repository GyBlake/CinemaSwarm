"""Test the panel's registered MCP tools and approval-bound rendering."""
import asyncio
import json

from mcp.shared.memory import create_connected_server_and_client_session

from cinemaswarm_world.collaboration import digest
from integrations.cinemaswarm_panel.server import RESOURCE, create_app


def test_panel_mcp_roundtrip(tmp_path):
    plans = tmp_path / "plans"
    plans.mkdir()
    path = plans / "wide.json"
    request = {"prompt": {"1": {"inputs": {}, "class_type": "LoadImage"}}}
    plan = {
        "shot_id": "wide", "episode_id": "demo", "request": request,
        "request_sha256": digest(request), "frame": {"filename": "wide.png", "references": []},
        "direction": "Wide", "preview": "data:image/png;base64,AA==",
    }
    path.write_text(json.dumps(plan))
    queued = []

    def comfy(url, payload):
        if url.endswith("/prompt"):
            queued.append(payload)
            return {"prompt_id": "wide-job"}
        return {"wide-job": {"status": {"status_str": "success", "completed": True},
                            "outputs": {"1": {"videos": [{"filename": "wide.mp4"}]}}}}

    server = create_app(tmp_path, "https://comfy.example.test", comfy)

    async def run():
        async with create_connected_server_and_client_session(server._mcp_server) as client:
            resource = await client.read_resource(RESOURCE)
            assert "CinemaSwarm" in resource.contents[0].text
            tools = {tool.name: tool for tool in (await client.list_tools()).tools}
            assert tools["open_production"].meta["ui"]["resourceUri"] == RESOURCE
            assert tools["queue_render"].meta["ui"]["visibility"] == ["app"]
            result = await client.call_tool("open_production")
            assert not result.isError, result.content
            assert result.structuredContent["shots"][0]["state"] == "Ready to queue"
            key = digest(plan)
            assert (await client.call_tool("queue_render", {"key": key})).isError
            assert not (await client.call_tool("approve_frame", {"key": key})).isError
            path.write_text(json.dumps({**plan, "direction": "Changed"}))
            assert (await client.call_tool("queue_render", {"key": key})).isError
            path.write_text(json.dumps(plan))
            result = await client.call_tool("queue_render", {"key": key})
            assert result.structuredContent["shots"][0]["state"] == "Rendered"
            assert "wide.mp4" in result.structuredContent["shots"][0]["video"]
            assert (await client.call_tool("queue_render", {"key": key})).isError

    asyncio.run(run())
    assert queued == [request]
