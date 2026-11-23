# CinemaSwarm Episode Renderer v1

The Episode Renderer is an **executable local assembly stage**. It uses FFmpeg
to concatenate author-approved still-frame assets on a deterministic timeline,
mixes provided WAV/FLAC audio or silence in preview mode, outputs MP4/H.264/AAC
and records a hash/probe receipt. It is NOT a generative motion or acting engine.

Run:
```bash
python cinema_swarm.py --render-episode ./private/episode-plan.json \
  --render-assets-root ./private \
  --episode-master ./private/build/episode-01.mp4 \
  --episode-receipt ./private/build/episode-01-receipt.json
```

Required local programs: `ffmpeg` and `ffprobe`. No provider keys or network
calls required. Example plan:
```json
{
  "version": 1, "episode_id": "lantern-01",
  "profile": "smoke-vertical-v1", "mode": "preview",
  "scenes": [
    {"scene_id": "arrival", "image_source": "stills/arrival.png", "duration_seconds": 3},
    {"scene_id": "discovery", "image_source": "stills/discovery.png", "duration_seconds": 4}
  ]
}
```

`smoke-vertical-v1`: 360×640, 12 fps, technical smoke use only.
`premium-vertical-v1`: 1080×1920, 30 fps, intended production format.
A `candidate` mode additionally requires each scene's explicit `approved:
true` and `continuity_report` with `checks_passed`, zero errors and unknowns,
plus `audio_source` and `captions_source`. This gates assembly of unapproved
materials but does not certify the finished content.

The renderer never creates fabricated human review scores or marks a film as
release-qualified. Receipts distinguish input integrity, actual stream probe,
timeline duration, generated silence, supplied captions, and remaining artistic
verification. Still-image shots have no authentic movement or lip-sync.
A scene-by-scene production plan is therefore **not** a completed full season.

The input asset root is restricted: absolute paths, traversal and symlink
escapes are rejected. Existing outputs are not overwritten by default.
Maximum 120 scenes, 30-minute cumulative duration, 100 MB per input source.
The render is staged in a temporary MP4 before publication; it is not
a multi-file atomic transaction with the receipt.
