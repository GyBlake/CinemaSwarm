# Narrative morphology and structural originality gate

This experimental module lets authors index **annotated plot structure**, rather than
only words, animation, setting, dialogue or character names.

## What is measured?

Each plot is represented as ordered beats with four explicitly authored fields:

- `function`: dramatic operation (setup, betrayal, revelation, reversal, etc.)
- `actor_role`: structural character function (protagonist, ally, antagonist, etc.)
- `outcome`: event consequence (loss, discovery, alliance, etc.)
- `cause`: zero-based index of a prior beat that causally motivates this one,
  or `null` for a root beat

The similarity score combines **75% ordered beat matching** (SequenceMatcher)
and **25% causal edge matching** (multiset Dice coefficient). It is deterministic
and only compares the author-supplied annotated structures; the tool does not
extract plot semantics from arbitrary screenplay prose.

Different names, visual design, settings, dialogue or platform packaging **do not**
change the score. Changed character agency, causal links, outcomes and dramatic
functions can change the score. The default rejection threshold is 0.85.

## Example candidate JSON

```json
{
  "version": 1,
  "story_id": "lantern-reveal",
  "beats": [
    {"function": "setup", "actor_role": "protagonist", "outcome": "loss", "cause": null},
    {"function": "inciting_incident", "actor_role": "ally", "outcome": "discovery", "cause": 0},
    {"function": "choice", "actor_role": "protagonist", "outcome": "sacrifice", "cause": 1}
  ]
}
```

Comparison library (local JSON only):

```json
{"version": 1, "stories": []}
```

## CLI integration

```bash
python cinema_swarm.py --dry-run \
  --morphology-candidate ./private/candidate.json \
  --morphology-library ./private/stories.json

# Combined with approved world-state input:
python cinema_swarm.py --dry-run \
  --world-snapshot ./private/world.json \
  --morphology-candidate ./private/candidate.json \
  --morphology-library ./private/stories.json
```

If a library story's score equals or exceeds the threshold, the CLI exits
with status **3**, printing the matching story ID and score. No provider is
called and no production packet is written. Otherwise the candidate structure
and a compact comparison report are added as **untrusted data** to the
Showrunner prompt. Both files are required together. Plain briefs continue
to work without morphology input.

## Scope and limitations

- This is a **heuristic structural gate**, not a plagiarism detector,
  copyright clearance tool or proof of creative originality.
- It cannot identify tropes absent from the local library or recognize
  incorrect/missing annotations. Human creative review is required.
- It does not mutate world canon, index external media, or scrape PineDrama.
- Store library data and private scripts locally; the approved live provider
  run sends the candidate's morphology fields and comparison report.
- Fictional archetype, astrology and numerology metadata remain optional
  symbolic story inputs and are not scientific personality predictors.
