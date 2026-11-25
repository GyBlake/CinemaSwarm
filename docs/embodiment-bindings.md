# Embodiment & Asset Binding Engine (experimental)

Each scene should derive appearance and equipment from independent sources:

| Owner | Canonical state |
| --- | --- |
| Identity | Immutable persona ID, name, instantiation, memory/history, identity image & voice signature |
| Body | Body ID, anatomical visual reference, body-specific vocal reference, physical metrics, worn clothing |
| Object | Object ID, visual anchor, condition, location, current holder body, owner identity and equipment slot |
| Presentation | Approved appearance/voice rendering asset and style references, scoped to identity |

The registry is intentionally separate from Persona Identity Registry. **Body
swapping exchanges occupants; it does not transport a coat or amulet worn on
a body.** Ownership does not imply physical possession. Physical form can
change (measurements, musculature, approved visual references) without
reassigning persona identity. Vocal anatomy follows body; a persona voice
anchor persists separately.

## Body swaps and continuity projection

```python
from cinemaswarm_world.identity import Identity, IdentityRegistry, Mutation
from cinemaswarm_world.embodiment import Body, Object, BindingRegistry, project_embodiment

t = "2026-01-01T00:00:00Z"
people = IdentityRegistry([
    Identity("mara", "Mara", t, "identity:face", "identity:voice", "body-a")
], t)
assets = BindingRegistry([Body("body-a", "face:body-a", "vocal:body-a")], [], t)
print(project_embodiment(people, assets))
```

Mutations are explicit, timestamped, provenance-linked and replayable.
An equipment slot is unique per body. A lost object requires recovery before
becoming worn or carried again. Invalid mutations roll back the whole pulse.
Assets are opaque references; the engine does not inspect or render images,
synthesize voice, or measure perceptual similarity.

## CLI production bridge

```bash
python cinema_swarm.py --world-snapshot ./private/world.json \
  --identity-snapshot ./private/identity.json \
  --asset-bindings ./private/assets.json --dry-run
```

Live external processing additionally requires `--approve-world-brief`,
`--approve-identity-brief`, and `--approve-asset-brief`. The bridge
uses verified snapshots and sends only selected participating characters.
No asset files are transmitted by this engine, only approved reference IDs.

## Audit boundaries

Old identity registry carries legacy persona-associated inventory and
physique. BindingRegistry is authoritative for **body-bound clothing, physical
measurements and actual object location** when supplied. A migration service
from older persona inventory will need explicit conflict resolution; no
silent migration or cross-ledger mutation is performed. Body/identity/bindings
must share a timestamp. The generated projection is a textual continuity
contract, not proof that final rendered frames/audio match it.
