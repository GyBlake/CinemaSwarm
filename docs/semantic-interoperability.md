# Semantic interoperability: intent -> expression -> manifestation

## Purpose
This is a **public, impersonal semantic translation contract** for CinemaSwarm.
Its governance process can be supported by a private institutional consultant,
but no proprietary agent identity, internal ontology, or private repository
content is included in the public runtime.

The **Rosetta Stone** bears a decree in three scripts: hieroglyphic,
Demotic and Ancient Greek. Correspondences between the versions assisted the
decipherment of Egyptian scripts. CinemaSwarm uses this as a **translation
analogy**, not as an ancient software specification: multiple agent-specific
representations of a scene preserve shared semantic identities and relations.
The historical scripts are not separate renderers or independent ontologies.

### Shared semantic pivot → equivalent production representations → reconciliation

1. **Origin** records the authorized authorial intent and provenance.
2. **Concepts** define a canonical semantic object, its polarity, scene, and
   evidence source. Authorial interpretation and documented cultural origins
   remain distinct.
3. **Relations** define `equivalent`, `depends_on`, `contradicts`,
   `transforms`, or `manifests_as`, with explicit rationale.
4. **Projections** compile the same concept IDs into image, voice, video,
   editing and continuity dialects. Two agents may receive radically different
   directions yet remain anchored to the same definition. Missing anchors,
   cross-scene mismatches or conflicting constraints fail validation.
5. **Evaluation** checks that reviewed outputs preserve the identified
   meaning, respect negative constraints, and carry no observed contradiction.

The layered distinction is required: **semantic ≠ transport ≠ execution ≠
presentation**. Producing JSON or a successful video call cannot independently
prove understanding, only an authorized interpretation and review process can
attest to it.

### Example
The *wing-like silhouette formed by two bodyguards* has an ordinary physical
explanation, an intentionally hidden supernatural correspondence, and a
later planned payoff. The image projection must preserve the two-bodyguard
geometry and forbid literal wings in the introduction. The soundtrack
projection can preserve a recurring motif, and the editor may preserve
ambiguity until the reveal. Their technical instructions differ while their
dramatic invariant remains the same.

### Commands

```bash
python cinema_swarm.py --prepare-semantics private/semantic.json \
  --semantic-package private/collaboration.json \
  --semantic-output private/semantic-projection.json

python cinema_swarm.py --audit-semantics private/semantic-eval.json \
  --semantic-contract private/semantic.json \
  --semantic-package private/collaboration.json \
  --semantic-output private/semantic-report.json
```

Candidate rendering and season qualification require both `semantic_contract`
and a matching passing `semantic_report`. Failing or missing reviewed
projections cannot be declared release-ready.

**Truth boundary:** This module checks schemas, authorized meaning mapping,
digest binding, overt contradictions and human attestations. It cannot
automatically measure subtle artistic interpretation or prove external model
cognition, and the public-private denylist is not comprehensive DLP. The
source of truth remains an authorized local contract, never a third-party
LLM's unreviewed output.

See `tests/gate_fixtures.py` and `tests/test_semantic_interop.py` for a
fully synthetic demonstration.

## Rosetta mapping example

A single semantic ID `hidden-wings` means *the audience sees the possibility
of wings, but is shown two ordinary guards as the immediate explanation*.
An image agent receives the silhouette geometry and lighting constraints;
a video agent receives the entrance timing and bodyguard blocking; an editor
receives a prohibition on revealing literal wings before the intended payoff;
a sound agent may receive a thematic motif without invoking a visible speaker.
Each projection references the same `hidden-wings` concept ID, so an approved
meaning can survive translation between production disciplines. A future
revelation is a separate causally linked concept, not a retroactive mutation
of the opening's approved audience knowledge.
