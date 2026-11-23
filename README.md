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
