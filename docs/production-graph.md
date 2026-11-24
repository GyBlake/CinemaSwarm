# Production object lineage: CinemaSwarm v1

## Rationale
The CinemaSwarm internal state already tracks world facts, character identities,
approved voices, and symbolic meaning. The missing operational link was **how
generation outputs and their exact references are reused and checked**, with
human-approved takes before editorial publication.

This original module adopts common film/VFX and software provenance patterns
also documented in Pine Drama Studio's public architecture and protocol,
without importing its source or claiming compatibility. Its upstream docs
were studied as an external reference, not added as a dependency.

## Workflow
1. Create public, versioned objects in dependency order. Permitted kinds:
   screenplay, bible, character, location, prop, scene, storyboard, keyframe,
   dialogue_audio, take, cut and subtitles.
2. Every object has a local file, SHA-256, and `inputs_sent_in_order`. The
   validator rejects duplicate, unresolved, forward and stale references.
3. A provider-produced output can include a receipt recording provider,
   request ID, exact ordered input hashes, reported USD cost, cost approval
   and human reviewer. This is declared evidence only and does not verify
   an external provider's private ledger.
4. The production stages `assets_planned`, `assets_approved`,
   `shots_planned`, `storyboard_approved`, and `takes_reviewed`
   each require explicit attributed human approval.
5. The editorial `cut` lists chosen take IDs. The same take IDs must be
   explicit inputs to the final cut asset. Other takes can remain recorded.
6. An offline audit rehashes all local files, rejecting missing or altered
   inputs and outputs. Candidate rendering and season qualification require
   a passing graph report bound to the graph digest.

These checks complement, rather than replace, existing creative-handoff,
voice/lip-sync, symbolic narrative, and audiovisual continuity audits.

### Offline CLI

```bash
python cinema_swarm.py --audit-production-graph private/production-graph.json \
  --production-root private --production-report private/production-report.json
```

Use `tests/gate_fixtures.py` for a deliberately synthetic JSON schema example.
Those example text files do **not** contain real video takes.

### Security and honesty
Production reports are local, attributable human/editor attestations with
file-integrity checks. No external paid generations or private Nexus data
are required; no claim of universal perceptual quality is made. Do not place
private Dreamcorp material in public graphs.

An outside service may not honor its declared input references; review the
actual returned video and voice artifacts before approving takes. This
implementation does not maintain automatic model session state, perform
Git 3-way merges, enforce provider account cost caps, or implement the Pine
protocol. For high-integrity production the report files should ultimately
be signed and independently verified rather than solely trusting JSON.
