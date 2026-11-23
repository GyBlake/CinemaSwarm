"""Create a non-cinematic, synthetic two-scene MP4 for CI smoke testing.

This synthetic asset proves only that our ffmpeg assembly and receipt contract
work. No fictional character identity or artistic benchmark is evaluated.
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw

from cinemaswarm_world.episode_renderer import render_episode


def main() -> None:
    root = Path("build/smoke")
    root.mkdir(parents=True, exist_ok=True)
    for index, color in ((1, "#14283b"), (2, "#49394f")):
        image = Image.new("RGB", (360, 640), color)
        drawing = ImageDraw.Draw(image)
        drawing.rectangle((32, 160, 328, 472), outline="#cfb578", width=5)
        drawing.text((55, 285), f"CinemaSwarm Test {index}", fill="white")
        image.save(root / f"scene-{index}.png")
    plan = {
        "version": 1, "episode_id": "smoke-ci-001",
        "profile": "smoke-vertical-v1", "mode": "preview",
        "scenes": [
            {"scene_id": "title", "image_source": "scene-1.png", "duration_seconds": 1.5},
            {"scene_id": "transition", "image_source": "scene-2.png", "duration_seconds": 1.5},
        ],
    }
    (root / "plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    receipt = render_episode(plan, root, root / "smoke-episode.mp4",
                             root / "receipt.json")
    print(json.dumps({"episode_id": receipt["episode_id"],
                      "duration": receipt["inspected"]["duration_seconds"],
                      "master_sha256": receipt["master_sha256"],
                      "quality": receipt["quality_evaluation"]}, indent=2))


if __name__ == "__main__":
    main()
