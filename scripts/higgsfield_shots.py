"""Plan, quote, submit, or check one CinemaSwarm render through Higgsfield MCP."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path

from cinemaswarm_world.higgsfield_adapter import (
    compile_plan, poll_shot, quote_shot, submit_shot,
)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


async def execute(args):
    if args.command == "plan":
        return compile_plan(read(args.handoff), read(args.bindings), model=args.model,
                            aspect_ratio=args.aspect_ratio, resolution=args.resolution)

    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    endpoint = os.getenv("HIGGSFIELD_MCP_URL", "https://mcp.higgsfield.ai/mcp")
    token = os.getenv("HIGGSFIELD_MCP_TOKEN")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    prefix = os.getenv("HIGGSFIELD_MCP_TOOL_PREFIX", "")
    async with streamablehttp_client(endpoint, headers=headers) as (incoming, outgoing, _):
        async with ClientSession(incoming, outgoing) as session:
            await session.initialize()
            loop = asyncio.get_running_loop()

            def call(operation, params):
                future = asyncio.run_coroutine_threadsafe(
                    session.call_tool(prefix + operation, params), loop,
                )
                result = future.result()
                if result.isError:
                    return {"error": "MCP tool rejected the request",
                            "details": [item.text for item in result.content if item.type == "text"]}
                if result.structuredContent is not None:
                    return result.structuredContent
                for item in result.content:
                    if item.type == "text":
                        try:
                            data = json.loads(item.text)
                        except ValueError:
                            continue
                        if isinstance(data, dict):
                            return data
                return {"error": "MCP returned no structured provider response"}

            if args.command == "status":
                return await asyncio.to_thread(poll_shot, read(args.receipt), call)
            shots = read(args.plan)["shots"]
            shot = next((item for item in shots if item["shot_id"] == args.shot), None)
            if shot is None:
                raise ValueError(f"unknown shot {args.shot}")
            if args.command == "quote":
                return await asyncio.to_thread(quote_shot, shot, call)
            return await asyncio.to_thread(
                submit_shot, shot, read(args.quote), call,
                max_credits=args.max_credits, ledger=args.ledger,
            )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("plan")
    plan.add_argument("handoff")
    plan.add_argument("bindings")
    plan.add_argument("--model", required=True)
    plan.add_argument("--aspect-ratio", default="16:9")
    plan.add_argument("--resolution", default="720p")
    for name in ("quote", "submit"):
        command = commands.add_parser(name)
        command.add_argument("plan")
        command.add_argument("shot")
        if name == "submit":
            command.add_argument("quote")
            command.add_argument("--max-credits", type=float, required=True)
            command.add_argument("--ledger", required=True)
    commands.add_parser("status").add_argument("receipt")
    try:
        print(json.dumps(asyncio.run(execute(parser.parse_args())), ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError, ImportError) as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
