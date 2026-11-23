# Semantic Dramaturgy Engine v1

**Purpose:** a deterministic diagnostic layer after manual literary-ontology
review and before CinemaSwarm production. Not an autonomous dramaturg,
character consciousness simulation, or replacement for professional critique.

## Data model

Use a version 1 morphology candidate (approved screenplay structural beats) and
a separate **author-controlled** JSON dramaturgy context. Example:

```json
{
  "version": 1,
  "story_id": "lantern-audit",
  "reviewed": true,
  "characters": ["mara", "archivist"],
  "facts": [{"id": "secret-map", "introduced_at": 1, "provenance": "approved-beat-1"}],
  "knowledge": [
    {"beat_index": 1, "audience": ["secret-map"],
     "characters": {"mara": [], "archivist": ["secret-map"]}}
  ],
  "stakes": [{"id": "archive", "owner": "mara", "introduced_at": 0,
              "resolved_at": null, "provenance": "approved-script"}],
  "transformations": [{"character_id": "mara", "from_archetype": "seeker",
                       "to_archetype": "guardian", "beat_index": 2,
                       "provenance": "author-reviewed"}],
  "motifs": [{"id": "map", "beat_indices": [0, 2], "provenance": "approved-script"}]
}
```

Facts are introduced at explicit beat indices; knowledge entries are
**snapshots**. Missing knowledge snapshots mean *unknown* and do not imply
ignorance. Perspective annotations differentiate audience-known/character-unknown
(dramatic irony) from character-known/audience-unknown (audience mystery).
The engine never invents internal character beliefs.

## Audit mode (offline, no provider)

```bash
python cinema_swarm.py --audit-dramaturgy ./private/candidate.json \
  --dramaturgy-context ./private/dramaturgy.json \
  --dramaturgy-output ./private/audit.json
```

The audit measures causal links, protagonist agency, repeated motifs, unresolved
stakes and explicitly annotated archetype transformations. It returns a
traceable diagnostics report. Missing annotations are reported as unknown, not
assigned fabricated values. TCE/RCI counters are **design analogies**, not a
claim that the virtual world is biologically alive.

## Showrunner connection

```bash
python cinema_swarm.py --dry-run \
  --dramaturgy-candidate ./private/candidate.json \
  --dramaturgy-context ./private/dramaturgy.json

# AFTER reviewing context and choosing external provider processing:
python cinema_swarm.py \
  --dramaturgy-candidate ./private/candidate.json \
  --dramaturgy-context ./private/dramaturgy.json \
  --approve-dramaturgy-brief
```

Live provider use requires `reviewed: true` and the additional explicit
`--approve-dramaturgy-brief` flag. Output is **read-only narrative advice**:
it cannot mutate a world-state ledger. Ordinary briefs, the morphology gate,
and optional world-state approval maintain their existing behaviors.

## Audit findings and limitations

- Evidence is **authored**, not extracted from private screenplay text automatically.
- The engine validates story IDs, beat indices, references, and provenance strings.
- It cannot establish psychological realism, creative originality, or factual
  astrology/numerology properties.
- The causal graph in morphology v1 holds at most one direct predecessor per
  beat. This limits representation of complex multi-causal scenes.
- Dramatic irony and mystery reflect supplied epistemic states, not mind-reading.
- A broad finding is editorial advice; no hard creative rejection is automatic.
- Keep client narrative assets and private Dreamcorp canon out of the public repo.
