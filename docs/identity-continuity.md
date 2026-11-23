# Character Identity & Continuity Registry v1

CinemaSwarm distinguishes persistent **persona identity** from mutable **embodiment**
and from the media used to depict it. Each identity is anchored by:

- immutable ID and instantiation timestamp
- canonical name (new nicknames are aliases, not identity replacements)
- face/reference asset anchor and voice signature reference
- original body vessel ID (current body may change)

The **face anchor** is a reference to the identity's approved canonical asset,
not a demand that every frame have identical anatomy. A visual renderer must
use current-body and current-appearance references to generate the on-screen
presentation. The voice anchor remains a character signature; vocal delivery
(pitch shift, mood, whisper, etc.) can evolve. Future production profiles can
separately model **body-specific vocal anatomy** from persona voice identity.

## Event-driven changes

Each mutation has a stable event ID, UTC timestamp, character ID, action,
structured data and nonempty provenance. Supported actions:

- `alias` (new public or private name; canonical name unchanged)
- `appearance` (clothing and reference image variant)
- `body_measure` (weight, height, musculature descriptor)
- `voice_delivery` (performance style and pitch shift)
- `relation` (relationship to another known identity)
- `skill` (learned, equipped, unequipped, enhanced, lost)
- `item` (carried, equipped, stored, lost + intact/damaged/enhanced/destroyed)
- `body_swap` (exchange two occupied body vessels, preserving both identities)
- `embody` (move an identity to a currently unoccupied body vessel)

Equipped inventory requires a slot; duplicate slots and possession conflicts
are rejected. Previously lost items require an explicit recovery flag.
Invalid operations roll back the complete pulse. Unknown entities, duplicate
events and backwards chronology fail closed.

## Restore / hydrate

```python
from cinemaswarm_world.identity import Identity, Mutation, IdentityRegistry

registry = IdentityRegistry([
    Identity("mara", "Mara", "2026-01-01T00:00:00Z",
             "face:approved-v1", "voice:signature-v1", "body-mara")
], "2026-01-01T00:00:00Z")
registry.pulse("2026-01-02T00:00:00Z", [
    Mutation("change-1", "2026-01-02T00:00:00Z", "mara",
             "appearance", {"clothing": "blue coat"}, "approved-script")
])
saved = registry.snapshot()
restored = IdentityRegistry.hydrate(saved)  # rebuilds and verifies event history
```

Hydration replays events from the immutable origin and refuses a snapshot whose
materialized view differs from replay. Snapshots are detached, not a database
transaction. Store assets privately and pass only approved identifiers in
production contexts. No face/voice synthesis or biometric matching occurs.

## Deliberate limits

This is an additive registry and does not yet automatically migrate historical
`World` snapshots or project identity details into the Showrunner. In a
transmigration event, mental and social identity stay with the identity ID,
while physical body ID changes; a downstream renderer needs a separate
body-appearance model for faithful visual continuity. Inventory currently
follows the persona rather than body location unless an explicit item event
updates it. This is a simplified v1 policy; body-tethered clothing and
accessories require a later location/ownership model.
