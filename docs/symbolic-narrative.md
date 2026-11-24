# CinemaSwarm Multimodal Symbolic Narrative Engine v1

## Meaning is constructed, not pasted onto a shot

The public engine uses twelve story-bearing channels: visual, acoustic,
kinetic, relational, temporal, numerical, spatial, linguistic, material,
psychological, cultural and cinematic. Symbols can be planted, echoed,
mirrored, inverted, disguised, amplified, transmuted, converged, diverged,
revealed and resolved. Each symbolic beat carries a scene/time window,
a literal explanation, dramatic purpose, an executable perception directive,
audience/character knowledge distinctions, authorial meaning, optional
numerical pattern and an explicit reveal policy.

**Example:** a wing silhouette is caused by two bodyguards (ordinary
surface explanation). Only in a later scene does an angelic identity become
literal. The first beat is `plant` + `conceal`; the later `reveal`
must depend on the seed. A premature reveal, impossible chronology,
unknown symbol, unseeded echo or contradictory reveal instruction
fails the authored symbolic plan validator.

## Culture, psychology and numerology

Numbers are recorded as count + arrangement + *author-supplied narrative
function*. Their meanings are not universal mathematical facts. Cultural
associations require named provenance and interpretation scope, never
a mandatory fixed numeric or religious interpretation. Different
characters may assign conflicting meanings to the same motif.
The interface permits open motifs with a future payoff episode without
claiming that an unrendered payoff has occurred.

## Full production quality gates

For every **candidate**, in addition to existing voice/continuity gates:

- `symbolic_program`: a public, episode-linked program whose SHA-256
  binding matches the collaboration package.
- `symbolic_report`: passing observed-shot audit with matching program and
  package digests, zero findings and no missing cue.
- Every observed cue has a real local evidence path and SHA-256 plus
  independently attributed human visual/audio semiotic review.
- Scene-level directives are generated for the external renderer; the
  provider does not gain MCP access and no internal thought is exposed.
- Season qualification also requires passing symbolic evidence per episode.

The audit can verify *file hashes and human-approved annotations*, but does
**not** automatically recognize metaphor, subliminal imagery, numeric design
or an audience's interpretation in video. Human approval is not a global
aesthetic guarantee. The legacy preview/synthetic workflow remains
available without asserting symbolic qualification.

## CLI

```bash
python cinema_swarm.py --prepare-symbolic ./private/symbolic.json \
  --symbolic-package ./private/collaboration.json \
  --symbolic-output ./private/symbolic-directions.json

python cinema_swarm.py --audit-symbolic ./private/symbolic-observations.json \
  --symbolic-plan ./private/symbolic.json \
  --symbolic-package ./private/collaboration.json \
  --symbolic-root ./private \
  --symbolic-output ./private/symbolic-report.json
```

The symbolic plan requires a `version` of 1, `episode_id`,
`package_sha256`, `visibility: public`, a `motifs` array and a `beats`
array. See `tests/gate_fixtures.py` and `tests/test_symbolic_narrative.py`
for complete valid, deliberately synthetic schemas.

All external distribution remains subject to explicit approval and the
same public/private boundary established by the collaboration gateway.
