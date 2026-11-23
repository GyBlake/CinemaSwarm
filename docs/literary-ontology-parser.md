# Literary ontology screenplay parser (experimental)

The parser is an offline, deterministic **first-pass reviewer assistant**,
not an LLM and not a reliable semantic interpreter of arbitrary scripts.
It recognizes limited dramatic cue vocabulary and outputs **proposed**
beat functions, actor roles, consequences and causal links with exact
line references, visible warnings and `approved: false` on every beat.

## Workflow: screenplay → review → approved candidate → originality gate

1. Save an original, authorized UTF-8 screenplay locally. Optional
   `ROLE Mara: protagonist` declarations help resolve archetypal roles.
2. Extract a draft:
   ```bash
   python cinema_swarm.py --extract-ontology ./private/script.txt \
     --ontology-story-id lantern-episode --ontology-output ./private/review.json
   ```
3. Examine every `evidence` entry in `review.json`. Correct the
   corresponding candidate beat's function, role, outcome and cause.
   **Causality is not inferred reliably**; specify a zero-based earlier
   beat index when a meaningful link exists. Set `approved: true`
   individually on all evidence entries after reviewing. Keep source
   line evidence and digest intact.
4. Finalize into a morphology candidate:
   ```bash
   python cinema_swarm.py --finalize-ontology-review ./private/review.json \
     --ontology-output ./private/candidate.json
   ```
   Finalization validates at least three beats, permitted values,
   chronological cause indices, at least one causal edge, and explicit
   approval for every beat. It does not alter the original script.
5. Run the existing gate:
   ```bash
   python cinema_swarm.py --dry-run \
     --morphology-candidate ./private/candidate.json \
     --morphology-library ./private/stories.json
   ```

## Boundaries

- Unrecognized events are omitted rather than fabricated.
- Lexical cues are fragile to figurative language, negation, complex
  cross-scene causality and ambiguous speakers. All guesses have **low
  confidence**. Even correct syntax is not proof of semantic accuracy.
- An author-approved candidate is **not** automatically promoted to
  virtual-world canon or added to the comparison library.
- Screening is limited to author-supplied reference structures and
  remains a heuristic, not copyright or plagiarism verification.
- Output text may contain private screenplays. The public repository
  includes only generic tests and documentation.
- No AI provider or video-rendering service is invoked by extraction
  or finalization.
