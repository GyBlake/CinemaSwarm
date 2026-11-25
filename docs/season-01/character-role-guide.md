# Æclyptic character role registry

## Dramatic-role taxonomy
This registry separates **story function**, **screen time**, **moral alignment**, **cultivation stage**, **awakening status**, and **Nexus access**. A deuteragonist is not necessarily less powerful than a protagonist; an antagonist need not be evil; an archetypal trickster or threshold keeper need not be an individual.

The versioned `character-roles.json` supplies **48 reusable roles**, **15 current entity assignments** and **10 relation edges**. Roles are a vocabulary, not a requirement to put a character into every slot. No romance is currently assigned.

### Primary narrative tiers
- Protagonist: **Nia**. Sole long-arc anchor; exclusive Nexus system bearer.
- Deuteragonist: **Mateo**, with his own rescue ethic and awakening.
- Tritagonist: **Mara**, the scientific and methodological counterweight.
- Ensemble leads: **Elias** (exploration) and **Leena** (knowledge, complicity and redemption).
- Parallel companion: **Vesper**, Nia's fallible metacognitive system voice.

### Opposition
- Primary human-directed opposing agency: **The Cartographer** (identity concealed) and **The Quiet Index** (institution).
- Field opposition / sympathetic antagonist: **The Keeper**, whose containment motive is intelligible but whose methods can violate consent.
- Environmental opposition: **The Crossing**, a fictional cosmological transition condition.
- Internal opposition: Nia's overreliance on records; Mateo's rescue compulsion; Elias's risk appetite; Leena's secrecy.

### Support and flexible functions
- Witness/informant: **Iris Bell** and Mrs. Baptiste.
- Mentor or compromised guide: **Leena**.
- Medical care/scholar: **Dr. Adewale Sanni**.
- Merchant/tempter: **The Crossing Market**.
- Historical archive/guardian: **The Meridian Archive**.
- Other supported genre functions include foil, rival, confidant, ally, herald, catalyst, threshold keeper, trickster, shapeshifter, traitor, redeemer, antagonist with empathetic motives, romance, sidekick, rescuer, target, victim, guest, cameo, narrator, chorus, and impersonal world antagonism.

## Production use
`cinemaswarm_world.character_roles.validate_character_roles(role_doc, season_handoff)` verifies original dramatic vocabulary, character assignments, relationships, the sole Nexus host and unchanged hidden identity. `character_role_observer` emits a read-only casting/continuity projection for scripting, prompting and production review. `tests/test_character_roles.py` exercises error cases. The registry is author-review draft data, not permission to auto-cast actors, expose secret identities, or revise scripts without review.

Different episodes can temporarily focus Mateo, Mara, Elias or Leena while **Nia remains the series protagonist**. Both the antagonist's motives and the ensemble's loyalties may evolve, but no author-approved twist is presumed.
