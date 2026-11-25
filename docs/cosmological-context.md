# Cosmological Context Engine (public, deterministic v1)

## Philosophy: world precedes story

CinemaSwarm already maintains event-sourced characters and time. The new
cosmological layer introduces a **causal setting** *before* the showrunner
selects or dramatizes events. Rather than force every series into a single
academy-leveling or holy-versus-demonic axis, writers may define multiple
coexisting institutions, interpretive traditions, recurring archetypes, and
contradictory beliefs.

The tool **does not infer real history or authenticate a cultural source**.
Imported references must be checked by a knowledgeable researcher or member of
the originating community, especially for living or sacred practices.

### Model

- `traditions`: cultural context, original versus historical sources, citation,
  interpretive scope, reviewer approval
- `laws`: fictional causal rules, distinct from beliefs or contested claims
- `archetypes`: ambient, sourced *functions*, never mandatory roles or
  assignments to characters
- `mappings`: approved comparative links: `functional_overlap`,
  `contrast`, or `adaptation`, explicitly recording differences
- `institutions`: situated belief systems that interpret the same world
  differently, without claiming every belief is physically true
- `events`: authorized, chronological, provenance-linked causes and
  consequences, without retroactive invention
- `governance`: an author approval receipt

The deterministic observer returns recent existing events, applicable laws,
the implicated institutions and a catalog of available ambient archetypes.
A world can contain schools, guilds, lineages, councils, libraries and multiple
explanations for the same event; no character must embody an archetypal trope.

The public format does not contain any private consultant, Dreamcorp
proprietary mythology, agent identity or unpublished system prompt.

### CLI

```bash
python cinema_swarm.py --observe-cosmology private/cosmology.json \
  --cosmology-output private/seeds.json
python cinema_swarm.py --cosmology-context private/cosmology.json --dry-run
python cinema_swarm.py --world-snapshot private/world.json \
  --cosmology-context private/cosmology.json --dry-run
```

For live AI generation, explicitly pass `--approve-cosmology-brief`; if
`--world-snapshot` is also given, the existing `--approve-world-brief`
authorization remains required. The companion world snapshot must have
the same world ID, active character IDs for event actors, and all reported
cosmological events committed in its canonical event log.

### Grounded distinctions

- A *real historical religious figure* is **not** assumed to equal a fictional
  character or a figure from another culture. Cross-cultural comparisons
  are qualified interpretations of functions, not historical identity.
- A fictional *world law* may be authoritative inside the story. A historical
  community's belief is not treated as an empirically verified supernatural law.
- Multiple mythic archetypes can be ambient and unselected.
- If sources conflict, preserve disagreement and its provenance instead of
  forcibly unifying them into a single lineage.
- The output is read-only input to the showrunner, never an autonomous
  world-state mutation. Output approval is necessary before promotion to canon.

### Demonstration

The regression fixture builds an **entirely original fictional world** with
an academy that treats dreams as navigable locations and a civic archive that
treats them as memories. An approved discovery causes disagreement without
inventing a holy-versus-evil villain. The archetypal interpreter and archivist
exist as available functions, not forced character roles.

### Limitations

No actual cultural corpus was fetched or authenticated for this implementation.
No automatic historical fact verification, ontology graph reasoning,
nonlinear causal simulation, AI character autonomy, game-engine scene
generation or native audiovisual model integration is claimed. A source URL
is a provenance pointer, not a verified citation.
