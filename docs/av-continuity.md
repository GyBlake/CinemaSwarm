# Audiovisual Continuity Validator v1

This module checks **declared rendered-shot metadata** against the authorized,
replay-verified world, persona and embodiment ledgers. It does not inspect
image pixels, identify people, compare vocal timbre, or certify a video's
perceptual fidelity. Hashes are integrity evidence, **not visual similarity**.

A versioned `shots.json` manifest requires `world_id`, `as_of` and
ordered `shots`. Each `shot` declares `shot_id`, increasing `index`,
and `cast` entries with identity_id, body_id, body_visual_anchor,
body_vocal_anchor, identity_voice_anchor, clothing, visible_equipment and
voice_active. Optional rendered_image_sha256/rendered_audio_sha256 support
separate exact-byte integrity checks.

## Verify offline

```bash
python cinema_swarm.py --validate-av-manifest ./private/shots.json \
  --world-snapshot ./private/world.json \
  --identity-snapshot ./private/identity.json \
  --asset-bindings ./private/assets.json \
  --av-report ./private/continuity-report.json
```

The operation produces a JSON report without any API key or provider call.
It returns 0 when metadata matches, 3 on declared continuity mismatch and 2
for invalid inputs. The report includes explicit differences and unknown
evidence without rewriting world canon.

The same-time snapshot contract means intentional transformations *between*
shots need a new time-specific approved projection. A body swap is evaluated
from its current approved body occupancy and physically worn equipment.
Missing visual/audio content hashes remain unverified, not proof of fidelity.

## Scope

- Pass means metadata agrees with source ledger; rendered pixels/audio may
  still be inconsistent.
- Does not extract metadata from video or classify voices.
- No production of facial embeddings or voiceprints.
- Never claims that a declared hash matches a real file unless
  `check_media_hash(file, expected_hash)` is explicitly invoked.
- No private production assets or canon shipped with the public repository.
