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
