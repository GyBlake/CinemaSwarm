# Media Evidence Analyzer (offline, experimental)

An evidence plan lists one or more **time-scoped shots**. Each shot references
its own approved world, identity, and body/object snapshots plus a single-shot
AV metadata manifest. Those snapshots must agree on the exact timestamp
and current character/body/item state. This allows authorized clothing changes,
body changes or transmigration *between shots*.

For each cast member, optional local reference and rendered evidence can be
paired as `image` (PNG/JPEG/etc supported by Pillow) or `audio` (16-bit
uncompressed PCM WAV). The analyzer reads **real image pixels or audio samples**,
compares aligned signal differences, and checks optional file SHA-256 hashes.

**Interpretation limit:** a signal difference is not proof that a *character*
or *speaker* changed. Camera movement, crop, lighting, lip movements, mixing
or timing can yield large differences. This module does **not** do facial
recognition, speaker verification, semantic object detection, video frame
extraction, animation tracking, or generalized perceptual identity scoring.

```bash
python cinema_swarm.py --analyze-media-evidence ./private/plan.json \
  --media-root ./private \
  --media-report ./private/evidence-report.json
```

The `plan.json` schema (example):

```json
{
  "version": 1,
  "image_threshold": 0.1,
  "audio_threshold": 0.1,
  "shots": [{
    "shot_id": "shot-1",
    "at": "2026-01-02T00:00:00Z",
    "world_snapshot": "world.json",
    "identity_snapshot": "identity.json",
    "asset_bindings": "bindings.json",
    "av_manifest": "shot-1-manifest.json",
    "media": [{
      "identity_id": "mara",
      "kind": "image",
      "reference": "approved/mara.png",
      "rendered": "renders/mara.png"
    }]
  }]
}
```

All file paths inside the plan are local, relative to `--media-root`;
resolved paths outside that root are rejected. File size and decoded-pixel
limits apply. Each manifest must contain exactly the corresponding shot.
Content digests support exact integrity, but not biometric identity inference.

**Exit statuses:** 0 = no evidence difference above selected thresholds;
3 = evidence requires review; 2 = malformed/inaccessible inputs.
The status `partial_evidence` means alignment is insufficient for comparison,
not that continuity passed.

No video is rendered, no media is uploaded, and no world canon is changed.
