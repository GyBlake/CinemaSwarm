# CinemaSwarm 🎬

**CinemaSwarm** is an experimental Python multi-agent production-planning application for serialized short-form cinema. An executive orchestrator delegates work to nine specialist agents covering narrative structure, continuity, symbolism, actor direction, cinematography, audience retention, social-platform packaging, production prompting, and quality control.

**What it produces:** text-based connected production packets and an optional
**local MP4 assembly** from supplied still images and audio. It does not
generate animated acting, lip sync, or production-quality AI cinematography,
nor certify finished visual identity consistency.

## Features

- Modular agent tools for nine creative-production disciplines
- Configurable UTF-8 story briefs
- Optional, read-only narrative world snapshot adapter with explicit approval for live context sharing
- Annotated plot morphology comparison and offline originality gate (requires an author-supplied reference library)
- Offline, evidence-linked screenplay-to-literary-ontology drafting with mandatory human beat review
- Read-only Semantic Dramaturgy audit for character knowledge, causal pressure, stakes, transformations, and motifs
- Replay-verified body-bound clothing, props, equipment slots and presentation asset references
- Safe offline request preview, without API keys or installed SDK packages
- Output path selection, no-clobber default, optional `--overwrite`
- Neutral sample project: **Lantern City**
- Unit tests and GitHub Actions CI

## Quick start

Requires Python 3.11 or later.

**Offline preview (no installation or API key):**

```bash
python cinema_swarm.py --dry-run
```

**Install and test:**

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

On Windows use `.venv\Scripts\activate` instead of the `source` command.

**Live generation:**

1. Set an `OPENAI_API_KEY` environment variable locally. Do not commit it.
2. Create a UTF-8 brief, e.g. `series.txt`, with your series title, premise, characters, style, and continuity rules.
3. Run:

```bash
python cinema_swarm.py --brief series.txt --output outputs/pilot.md
```

Live generation uses the OpenAI Agents SDK and may incur API charges. The default series brief is optional. To replace an existing output, add `--overwrite`.

## Experimental world → screenplay integration

```bash
# Preview the Showrunner's world-informed prompt without installing the SDK
python cinema_swarm.py --world-snapshot ./private/world.json --dry-run
# After reviewing the preview, explicitly approve live external processing
python cinema_swarm.py --world-snapshot ./private/world.json --approve-world-brief
```

Generate a `world.json` file with `World.to_json()` (see
[world engine docs](docs/world-engine.md)). No snapshots are included in the
repository. Live use sends the selected story context to an AI provider and may
incur charges. The current pipeline still produces text packets, not video.

## Narrative morphology originality check

Compare a candidate's annotated dramatic functions, character roles, outcomes,
and causal links against a **local reference library** before generation:

```bash
python cinema_swarm.py --dry-run \
  --morphology-candidate ./private/candidate.json \
  --morphology-library ./private/library.json
```

The gate blocks high structural similarity (exit code 3, default score threshold
0.85). It ignores mere changes in names, dialogue or visual style. It is an
author-supplied heuristic and **not** copyright clearance or universal
originality detection. See [morphology docs](docs/narrative-morphology.md).

## Screenplay → reviewed literary ontology

```bash
python cinema_swarm.py --extract-ontology ./private/script.txt \
  --ontology-story-id pilot --ontology-output ./private/review.json
# Edit review.json, verify dramatic functions and cause links,
# then set each evidence entry's approved flag to true.
python cinema_swarm.py --finalize-ontology-review ./private/review.json \
  --ontology-output ./private/candidate.json
```

This first-pass **low-confidence lexical parser** emits line-linked draft
proposals, not an authoritative interpretation of an arbitrary screenplay.
Finalized, explicitly reviewed candidates can be checked with the existing
morphology similarity gate. [Parser guide](docs/literary-ontology-parser.md).

## Semantic dramaturgy (offline review and optional production context)

After reviewing the screenplay ontology candidate, supply explicit dramatic
annotations for known character facts, stakes, archetypal changes and motifs:

```bash
python cinema_swarm.py --audit-dramaturgy ./private/candidate.json \
  --dramaturgy-context ./private/dramaturgy.json \
  --dramaturgy-output ./private/audit.json
```

To include author-reviewed dramaturgy diagnostics in a production request,
provide both `--dramaturgy-candidate` and `--dramaturgy-context`. Live external
processing additionally requires `--approve-dramaturgy-brief`.
See [dramaturgy guide](docs/semantic-dramaturgy.md).

## Embodiment and asset bindings

When a production includes transmigration or physical continuity changes,
provide a separate body and object ledger alongside world and identity state:

```bash
python cinema_swarm.py --world-snapshot ./private/world.json \
  --identity-snapshot ./private/identity.json \
  --asset-bindings ./private/assets.json --dry-run
```

Body-worn objects remain with the body through body swaps. Identity memories,
name and voice signature remain with the persona. Live external data use
requires `--approve-world-brief`, `--approve-identity-brief`, and
`--approve-asset-brief`.
[Embodiment documentation](docs/embodiment-bindings.md).

## Offline audiovisual continuity manifest validation

Compare *declared* shot metadata to the replay-verified world/identity/body
state without a provider call:

```bash
python cinema_swarm.py --validate-av-manifest ./private/shots.json \
  --world-snapshot ./private/world.json \
  --identity-snapshot ./private/identity.json \
  --asset-bindings ./private/assets.json \
  --av-report ./private/continuity-report.json
```

This detects metadata mismatches in body occupancy, reference assets, voice
signature IDs, clothing and worn equipment. It **does not inspect rendered
pixels or audio timbre**. See [AV continuity guide](docs/av-continuity.md).

## Experimental media evidence inspection

Inspect actual local image pixels and uncompressed PCM WAV audio signals against
approved references, with **a separate canonical snapshot per shot**:

```bash
python cinema_swarm.py --analyze-media-evidence ./private/plan.json \
  --media-root ./private --media-report ./private/evidence-report.json
```

This produces generic signal differences, hash-integrity reports and canonical
metadata checks. It does **not** recognize character faces or verify speaker
identity. [Media evidence guide](docs/media-evidence.md).

## Evidence-first season benchmark audit

The optional `--audit-season` mode examines a versioned multi-episode manifest,
inspects real media streams with local `ffprobe`, verifies files and documented
human reviews, and refuses to certify incomplete seasons or missing measurements.

```bash
python cinema_swarm.py --audit-season ./private/season.json \
  --benchmark-root ./private --benchmark-report ./private/season-audit.json
```

Profiles are **internal studio gates**, not worldwide platform certification.
The project still does not render full seasons.
[Benchmark program](docs/cinema-benchmarks.md).

## Executable local episode assembly

Assemble a short MP4 episode from authorized scene stills and a provided
soundtrack (or generated silence in technical preview mode):

```bash
python cinema_swarm.py --render-episode ./private/episode-plan.json \
  --render-assets-root ./private \
  --episode-master ./private/build/episode.mp4 \
  --episode-receipt ./private/build/episode-receipt.json
```

This FFmpeg stage provides a **real rendering smoke test**, a checked duration
and master SHA-256. It cannot manufacture character animation or satisfy the
studio quality score by itself. [Renderer contract](docs/episode-renderer.md).

## Testing-ready synthetic episode

CI installs FFmpeg, runs actual MP4 assembly tests (not skipped), generates a
short **synthetic** 360 × 640 preview using `scripts/create_episode_smoke.py`,
and publishes the MP4, plan, and SHA-256 receipt as an Actions artifact.

The preview is deliberately **not** a film or character-rendering
demonstration and receives no artistic score. It is a reproducible technical
test proving that assets can be assembled, measured and audited.

## External agent context and speaker protection

Sanitized collaboration contracts, approved provider interpretations, and
human-reviewed voice/lip-sync evidence now gate **candidate** renders and
season qualification. Speakers have locked voice IDs and explicit channel
routing for onscreen, offscreen, thought, crowds and disembodied narration.

`--prepare-collaboration`, `--verify-collaboration` and
`--audit-performance` produce receipts. External providers do not
automatically inherit the repo, model internals or MCP tools.
See [agent hydration and performance gates](docs/agent-hydration.md).

## Multimodal symbolic narrative and foreshadowing

`cinemaswarm_world/symbolic_narrative.py` tracks scene-bound symbolic
beats across twelve channels (visual, acoustic, kinetic, relational,
temporal, numerical, spatial, linguistic, material, psychological,
cultural and cinematic) with plant/echo/mirror/invert/disguise/amplify/
transmute/converge/diverge/reveal/resolve operators.

Symbolic cues require explicit dramatic purpose, audience/character
knowledge distinctions, culturally attributed interpretation and
ordered dependencies. Reviewed shot evidence is required for candidate
rendering and season qualification; a missing or contradicted symbol
prevents a release pass. This is a reviewer-verified semantic gate,
**not** automatic pixel-level symbolic recognition.

See [multimodal symbolic storytelling](docs/symbolic-narrative.md).

## Versioned production graph and take selection

CinemaSwarm has a versioned, provider-neutral production-object graph:
explicit ordered references to upstream character/scene/storyboard assets,
per-output source SHA-256 integrity, optional provider call receipts with
reported costs and approvals, mandatory production review stops, and
an explicit selected take list for the final cut.

This is an original production-control implementation informed by publicly
documented filmmaking patterns, **not** an import of Pine Drama Studio
or compatibility with the Pine proprietary service.

`python cinema_swarm.py --audit-production-graph ./private/graph.json
--production-root ./private --production-report ./private/report.json`

Candidate rendering and season qualification require passing graph receipts.
See [production object graph](docs/production-graph.md).

## Semantic interoperability and meaning preservation

CinemaSwarm supports an original public semantic-contract boundary inspired
by the *Rosetta Stone* as an analogy for cross-language meaning alignment.
It is not an ancient software specification. A versioned contract separates authorial
intent, defined concepts, polarities, relations, and provider-specific
execution projections. It keeps semantic, transport, execution and
presentation layers distinct.

`--prepare-semantics` exports authorized instructions;
`--audit-semantics` validates signed-off human interpretation against
meaning-preservation and non-contradiction requirements. Candidate rendering
and season qualification now require passing semantic evidence.

See [semantic interoperability](docs/semantic-interoperability.md).

## Seven-stage studio execution and continuity controls

Beyond existing canonical world, body, voice, symbolism, Rosetta translation
and release-gate contracts, CinemaSwarm now implements a **provider-neutral**
execution and review runtime in `cinemaswarm_world/studio_runtime.py`:

- Authorized jobs with frozen SHA-256 input references, stable idempotency
  keys, explicit dependency preflight, cost ceilings and attributed review.
- Immutable reference assets and per-provider returned media asset receipts;
  digest and provider input matching required for a `verified` state.
- On-disk atomic snapshots and checkpoints; no automatic network calls.
- Targeted failed/rejected job repair plans with bounded retries and budget
  rechecking, preserving other approved assets.
- `media_qc.py` inspects **actual local video** for codec/container readability,
  stream existence, measured duration/resolution, and inter-frame pixel motion.
  This does not perform facial recognition, speaker authentication or
  audiovisual phoneme alignment.
- `series_ledger.py` reconciles approved delayed symbolic payoff obligations
  across a contiguous set of episodes; unresolved obligations become blocking
  when their deadline is reached.

Commands: `--audit-runtime`, `--plan-repair`, `--inspect-clips`,
`--audit-series-ledger`. For contracts and limitations see
[studio fulfillment](docs/studio-fulfillment.md).

## Structured shot execution and provider handoff

`cinemaswarm_world/shot_execution.py` implements a public, original
**Shot Execution Contract** that aligns each production shot with:
- Exact scene timing, character IDs and previously approved voice IDs.
- Ordered SHA-256 asset references to the production object graph.
- Active dialogue with authoritative speaker, channel and timing.
- Blocking, camera, location, initial and final scene/prop/character states.
- Acoustic instructions, negative constraints and approved symbolic cues.
- Rosetta semantic projection IDs for image/voice/video/editing/continuity.
- Reviewer-attested output evidence that can block candidate rendering and
  season qualification when required approval dimensions fail.

Use `--prepare-shots` with `--shot-package`, `--shot-semantic`,
`--shot-symbolic`, `--shot-graph` and `--shot-output` to compile vendor-neutral
provider instructions. Add `--shot-reviews` to audit a human-reviewed
production. See [structured shot execution](docs/shot-execution.md).

This adapts general production principles described in Pine Drama Studio's
public tooling documentation, **not its proprietary runtime or model routing**.

## Cosmological Context Engine: world before story

`cinemaswarm_world/cosmological_context.py` introduces a deterministic,
**author-controlled, provenance-preserving** world context upstream of story
creation. It models fictional laws, documented traditions and interpretations,
ambient functional archetypes, comparative relationships, institutions and
approved causal events. Narrative observers select *existing events* instead
of fabricating new canon. Historical or sacred traditions are **never silently
equated** with original fiction; comparative mappings preserve differences and
require human approval.

```bash
python cinema_swarm.py --observe-cosmology ./private/cosmology.json \
  --cosmology-output ./private/cosmology-seeds.json

python cinema_swarm.py --cosmology-context ./private/cosmology.json --dry-run

# Optional: attach to a committed, same-world event history
python cinema_swarm.py --cosmology-context ./private/cosmology.json \
  --world-snapshot ./private/world.json --dry-run
```

Live AI-provider use requires explicit `--approve-cosmology-brief`. This is
a read-only narrative-context adapter, not an autonomous mythological simulator.
See [cosmological context specification](docs/cosmological-context.md).

## Æclyptic awakening and DNA LLM companion continuity

`cinemaswarm_world/awakening.py` adds an author-reviewed **fictional**
awakening registry layered on top of the Cosmological Context Engine.
It tracks celestial geometry, radiation categories and other triggering
conditions as **fictional narrative causes**, plus individual susceptibility,
somatic/gut-brain signaling, metacognitive waking-dream system interfaces,
organic companion identities and stateful awakening sequences. Noncoding DNA
regulation, stress biology and the gut–brain axis are scientific analogies,
**not evidence** that eclipses, hazardous radiation or psychological trauma
activate superhuman capabilities.

```bash
python cinema_swarm.py --observe-awakenings \
  --awakening-registry ./private/awakenings.json \
  --awakening-cosmology ./private/cosmology.json \
  --awakening-output ./private/awakening-observer.json

python cinema_swarm.py --cosmology-context ./private/cosmology.json \
  --awakening-registry ./private/awakenings.json --dry-run
```

For live provider generation, both `--approve-cosmology-brief` and
`--approve-awakening-brief` are required. See
[awakening registry specification](docs/awakening-registry.md).

## Architecture

```text
Series Brief -> Request Builder -> Executive Orchestrator
                                      |-- Story Structure
                                      |-- Continuity
                                      |-- Symbolism
                                      |-- Performance
                                      |-- Cinematography
                                      |-- Retention
                                      |-- Platform Packaging
                                      |-- Production Prompting
                                      '-- Quality Control
                                    -> Production Packet (.md)
```

The specialist agents are delegated through the Agents SDK and are constructed only during a live run. The offline `--dry-run` prints the composed request and never calls an AI provider.

## Current engineering limitations

- Agent responses are free-form text. A strict machine-validated packet schema is planned.
- A full real-provider integration run and media-rendering pipeline are not yet proven.
- API cost measurement and rendered-frame continuity checking are not implemented.
- Dependencies use bounded version ranges rather than a fully reproducible lockfile.
- Generated creative outputs should be reviewed by a human prior to production.

## Security and data handling

No credentials, proprietary briefs, character assets, or generated client content are bundled. Keep local `.env` files and production packets private. External AI services may process submitted briefs and prompts; consult their applicable data terms before using confidential material. Treat externally supplied briefs and model outputs as untrusted data.

## License

This project is distributed under the **Eclipse Public License 2.0**. See [LICENSE](LICENSE).

## Season 01 dramatic character roles

The Æclyptic development package includes a [48-role dramatic taxonomy](docs/season-01/character-role-guide.md), [15 assigned characters/institutions/forces](docs/season-01/character-roles.json), and 10 relationship edges. The independent `cinemaswarm_world.character_roles` validator cross-checks the [eight-episode season handoff](docs/season-01/season-handoff.json), maintains Nia's sole Nexus protagonist status and preserves antagonist identity secrecy. Assignments remain **draft**, not final casting or completed scenes.

## Camera Engineer virtual cinematography stack

The [Æclyptic Camera Engineering Stack](docs/season-01/camera-engineering-stack.md)
provides read-only numeric checks on the
[Episode 01 camera manifest](docs/season-01/e01-camera-engineer.json):
virtual crew department responsibilities, room anchors, lens and
focus target configuration, camera positions and heights, shot size,
180° action-axis and dolly path, subjective versus objective character
visibility, and 40-second parent shot coverage. It validates the
[contact proof](docs/season-01/nia-vesper-contact.json) and preserves
**audience-visible Vesper** without making her visible to bystanders.
This is previsualization metadata, not a 3D film renderer, virtual
cinematography simulation or real calibrated camera setup.

## Studio OS crew handoff bus

The [CinemaSwarm crew architecture](docs/season-01/studio-os-crew-integration.md) routes the [18 functional departments](docs/season-01/studio-crew.json) through a **single validated shared scene state** instead of eighteen unrelated prompt contexts. `cinemaswarm_world.studio_crew.compile_department_handoffs` produces deterministic crew packets from the current Æclyptic contact proof, cast, stage, and camera engineering inputs. `runtime_bridge` only reports jobs already authorized by the separate production runtime. No actors, stagehands, video vendors or external providers are automatically invoked by compiling a handoff; all results remain in preproduction until human-reviewed receipts exist.
