# Shot Execution Contract v1

A versioned public provider-neutral shot handoff that turns approved
narrative semantics into **the exact references and scene transitions a
rendering department needs**.

The design incorporates generally documented production patterns (presets,
references, blocking, first and exit states) studied from Pine Drama Studio's
public [preset documentation](https://github.com/PineComputer/pine-drama-studio/blob/main/doc/presets.md).
CinemaSwarm implements its own schemas and validators; it does not copy
Pine's private `drama-cli`, invoke its model sets or claim API compatibility.

## Hydration inputs
A shot contract references **the exact SHA-256** of four canonical contracts:

- Authorized public collaboration package: character/voice identities,
  scenes and line timings.
- Rosetta semantic contract: canonical concept IDs and stage-specific
  meaning preservation/negative claims.
- Symbolic program: modality, concealment/reveal policy, foreshadow
  event timing and perceptual instructions.
- Production graph: recorded, ordered, hash-bound reference media.

Any changed source invalidates the shot plan until it is explicitly rebuilt
and reapproved. No private Nexus data is exported.

## Shot schema
Every shot carries `id`, `scene_id`, `start_ms`, `end_ms`, `cast`,
`asset_refs`, `dialogue_ids`, `symbolic_beat_ids`,
`semantic_projection_ids`, `location`, `camera`, `blocking`,
`initial_state`, `exit_state`, `soundscape` and
`negative_constraints`.

State objects specify `character_positions`, `prop_state`, and
`environment_state`. Every spoken line and symbolic beat in the episode
must be assigned to a shot without crossing its time/scene window.
Every shot must carry an image or video semantic meaning projection.
Voice IDs are sourced from the cast contract, not re-invented by the
video generation prompt. Stale or duplicate asset references are rejected.

## Stage projection
`stage_handoffs` emits ordered per-shot provider-agnostic handoffs with
reference input hashes, soundtrack instructions, line IDs/voices, camera,
blocking, start/exit state, symbol reveal policy and authorized semantic
constraints for image, voice, video, editing and continuity roles.

```bash
python cinema_swarm.py --prepare-shots private/shots.json \
  --shot-package private/collaboration.json \
  --shot-semantic private/semantic.json \
  --shot-symbolic private/symbolic.json \
  --shot-graph private/production-graph.json \
  --shot-output private/provider-shots.json
```

To audit:
```bash
python cinema_swarm.py --prepare-shots private/shots.json \
  --shot-package private/collaboration.json \
  --shot-semantic private/semantic.json \
  --shot-symbolic private/symbolic.json \
  --shot-graph private/production-graph.json \
  --shot-reviews private/shot-reviews.json \
  --shot-output private/shot-quality.json
```

### Fail-closed acceptance
Candidate rendering and season benchmark qualification both require the
bound shot contract and passing shot review. Failed identity, environment,
dialogue, transition, symbolism or semantic review blocks release.

**Honest limits:** The shot evidence manifest is reviewer-attested and
hash-identified. It does not automatically compare faces or mouths to the
approved imagery, measure phonemes, or independently validate cinematic
quality. The current local renderer still assembles still images and audio;
this shot contract does not secretly provide a working AI-video backend.

## Higgsfield rendering

Use the provider handoff emitted by `--prepare-shots`. Seed and approve the
sets, cast and recurring props first. For each source object, record its
production-graph SHA-256 and the Higgsfield UUID of the corresponding
uploaded image or saved Element. Keep this file private.

```json
{
  "the-ring-cassette": {
    "sha256": "<exact SHA-256 from the production graph>",
    "role": "ref_element",
    "value": "<Higgsfield Element UUID>"
  }
}
```

Reuse the same object ID in each shot that needs the same prop. The adapter
resolves it to the same provider ID across scenes and blocks missing or
stale bindings. Select a model that accepts your bound media roles. A model
that supports a single start image cannot consume separate set and prop
references. The render is rounded up to whole seconds with a three-second
minimum. Retain the original timing for the edit.

```bash
python -m scripts.higgsfield_shots plan private/provider-shots.json \
  private/higgsfield-bindings.json --model YOUR_MODEL > private/higgsfield-plan.json
```

Planning works offline. Live commands need the Python `mcp` package and an
authenticated streamable HTTP MCP connection that exposes
`estimate_video_cost`, `generate_video`, and `jobs_wait`. Set
`HIGGSFIELD_MCP_URL` for a different endpoint,
`HIGGSFIELD_MCP_TOKEN` if the connection provides a bearer token, and
`HIGGSFIELD_MCP_TOOL_PREFIX` if the tool names are namespaced. The default
URL is the [official Higgsfield MCP endpoint](https://mcp.higgsfield.ai/mcp).
This client does not implement interactive OAuth. Live calls through the
ChatGPT connector and authenticated calls from a standalone Python
process are separate connections.

```bash
python -m scripts.higgsfield_shots quote private/higgsfield-plan.json SHOT_ID > private/shot-quote.json
python -m scripts.higgsfield_shots submit private/higgsfield-plan.json SHOT_ID \
  private/shot-quote.json --max-credits APPROVED_LIMIT --ledger private/render-ledger \
  > private/shot-receipt.json
python -m scripts.higgsfield_shots status private/shot-receipt.json
```

Pass the credit limit only after reviewing the shot and quote. The adapter
refreshes the quote before submission and stops if the price increases.
Keep a single shared ledger for the production. A claimed request with
no job receipt needs reconciliation against Higgsfield history before any
retry. Use the returned media for the existing continuity review before
cutting it into the episode. Voice and dialogue assignments remain in the
plan for editorial. The adapter requests picture with separate dialogue
and does not assert that Higgsfield followed the prompt.
