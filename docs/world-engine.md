# CinemaSwarm narrative world kernel (experimental)

This additive, offline Python package introduces **world-state before screenplay**:
persisted entities, temporal origins, explicit events, provenance, memory, and
an observer that converts committed events into factual scene seeds.

## Architecture

- **Origination**: instantiate characters with stable IDs, UTC origins, motivations,
  archetypes and explicitly authored symbolic profiles.
- **Sustenance**: preserve world time, relationships, memories and immutable event
  records across production pulses.
- **Transformation**: apply validated choices, conflicts, revelations and relationship
  events; roll back an entire pulse if validation fails.
- **Circulation**: the pulse returns explicit counts, including total committed events.

These names are design analogies to the Trimurti–Tridevi and reciprocal
circulation discussions. This module does not claim to simulate consciousness,
astrological causality or autonomous continuous life. Astrology/numerology are
optional fictional metadata, never inferred or used as factual predictors.

## Minimal offline example

```python
from cinemaswarm_world import World, Character, Event

world = World("lantern-city", "2026-01-01T00:00:00Z")
world.instantiate(Character("cartographer", "The Cartographer",
                            "2026-01-01T00:00:00Z",
                            archetypes=["seeker"], motivations=["find the missing street"]))
world.pulse("2026-01-02T08:00:00Z", [
    Event("reveal-1", "2026-01-02T08:00:00Z", "cartographer",
          "revelation", detail="The street vanished overnight.",
          provenance="approved-series-bible")
])
print(world.narrative_observer())
print(world.to_json())
```

## Connect to the Showrunner (explicit, review-gated)

The optional adapter reads a **local** world snapshot and projects up to five
chronological events with participating character metadata and provenance into
a read-only prompt. The Showrunner receives this context through the existing
executive orchestrator. No world mutation occurs during generation.

```bash
# Export a World instance to a JSON file under a private local path first.
python cinema_swarm.py --world-snapshot ./private/world.json --dry-run

# Review the preview carefully; only then authorize sending the same data to a provider:
python cinema_swarm.py --world-snapshot ./private/world.json \\
  --approve-world-brief --brief ./private/story.txt --output ./private/episode.md
```

The approval flag is required for **live** world-context generation, not for
local dry runs. Any world snapshot is untrusted input, and the adapter validates
character references, chronological event ordering, origins, and provenance
field shape before constructing the request. Do not commit snapshots or expose
sensitive world state to third-party services without authorization.

**Boundary:** world-state writes are explicit and authored. The adapter is
read-only and outputs a text production packet, not a canonical world-state
mutation. Produced scene dramatizations require human review before promotion
to canon.

**Security:** no proprietary character canon, credentials, prompts or private
repository metadata are embedded in this package. Output snapshots can contain
user-supplied story data and should not be committed automatically.

**Limitations:** snapshots are returned as JSON but durable DB storage, replay,
concurrent transactions, simulation physics, agent autonomy, render pipeline,
and schema version migrations remain future work.
