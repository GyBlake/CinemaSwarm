# CinemaSwarm 🎬

**CinemaSwarm** is an experimental Python multi-agent production-planning application for serialized short-form cinema. An executive orchestrator delegates work to nine specialist agents covering narrative structure, continuity, symbolism, actor direction, cinematography, audience retention, social-platform packaging, production prompting, and quality control.

**What it produces:** a text-based, five-clip production packet with a connected storyline and scene-level production prompts. It **does not render video** or verify final visual identity consistency.

## Features

- Modular agent tools for nine creative-production disciplines
- Configurable UTF-8 story briefs
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
