"""Replayable body, prop and visual/voice asset bindings for CinemaSwarm.

A persona owns identity and memories; a body owns anatomy, clothing and worn
equipment; an object owns condition and location. Asset references are opaque
approved IDs: this module never generates, opens or matches biometric media.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import copy
import json
from pathlib import Path

from .identity import IdentityRegistry, utc, _required

CONDITIONS = frozenset({"intact", "damaged", "enhanced", "destroyed"})
LOCATIONS = frozenset({"worn", "carried", "stored", "ground", "lost", "destroyed"})
MAX_EVENTS = 10000
MAX_BYTES = 2_000_000


@dataclass(frozen=True)
class Body:
    id: str
    visual_anchor: str
    vocal_anchor: str
    clothing: str = "unspecified"
    weight_kg: float | None = None
    height_cm: float | None = None
    muscle: str = "unspecified"

    def __post_init__(self):
        _required(self.id, "body ID")
        _required(self.visual_anchor, "body visual anchor")
        _required(self.vocal_anchor, "body vocal anchor")


@dataclass(frozen=True)
class Object:
    id: str
    visual_anchor: str
    condition: str
    location: str
    holder: str | None = None
    slot: str | None = None
    owner: str | None = None

    def __post_init__(self):
        _required(self.id, "object ID")
        _required(self.visual_anchor, "object visual anchor")
        if self.condition not in CONDITIONS or self.location not in LOCATIONS:
            raise ValueError("invalid object condition or location")


@dataclass(frozen=True)
class BindingEvent:
    id: str
    at: str
    action: str
    target: str
    data: dict
    provenance: str

    def __post_init__(self):
        _required(self.id, "binding event ID")
        _required(self.target, "binding target")
        _required(self.provenance, "provenance")
        if self.action not in {"body_change", "object_change", "presentation"}:
            raise ValueError("invalid binding action")
        if not isinstance(self.data, dict) or not self.data:
            raise ValueError("binding data must be a nonempty object")
        object.__setattr__(self, "at", utc(self.at))


class BindingRegistry:
    def __init__(self, bodies: list[Body], objects: list[Object], started_at: str):
        self.started_at = utc(started_at)
        self.time = self.started_at
        self.bodies = {x.id: asdict(x) for x in bodies}
        self.objects = {x.id: asdict(x) for x in objects}
        if len(self.bodies) != len(bodies) or len(self.objects) != len(objects):
            raise ValueError("duplicate body or object ID")
        self.origins = {"bodies": [asdict(x) for x in bodies],
                        "objects": [asdict(x) for x in objects]}
        self.presentations: dict[str, dict] = {}
        self.events: list[BindingEvent] = []
        self._validate_objects()

    def _validate_objects(self):
        occupied = set()
        for obj in self.objects.values():
            place, holder, slot = obj["location"], obj["holder"], obj["slot"]
            if obj["owner"] is not None:
                _required(obj["owner"], "owner")
            if place == "worn":
                if holder not in self.bodies:
                    raise ValueError("worn object requires known body holder")
                _required(slot, "equipment slot")
                key = (holder, slot)
                if key in occupied:
                    raise ValueError("duplicate body equipment slot")
                occupied.add(key)
            elif place == "carried":
                if holder not in self.bodies or slot is not None:
                    raise ValueError("carried object requires body holder, no slot")
            elif holder is not None or slot is not None:
                raise ValueError("unworn object cannot retain holder or slot")
            if obj["condition"] == "destroyed" and place not in {"destroyed", "lost"}:
                raise ValueError("destroyed object cannot be in use")
            if place == "destroyed" and obj["condition"] != "destroyed":
                raise ValueError("destroyed location requires destroyed condition")

    def _apply(self, event: BindingEvent):
        data = event.data
        if event.action == "body_change":
            if event.target not in self.bodies or set(data) - {
                "visual_anchor", "vocal_anchor", "clothing",
                "weight_kg", "height_cm", "muscle"
            }:
                raise ValueError("invalid body change")
            body = self.bodies[event.target]
            for key, value in data.items():
                if key in {"weight_kg", "height_cm"}:
                    if type(value) not in (int, float) or not 0 < value <= (
                        1500 if key == "weight_kg" else 10000
                    ):
                        raise ValueError("invalid body measurement")
                else:
                    _required(value, key)
                body[key] = value
        elif event.action == "object_change":
            if event.target not in self.objects or set(data) - {
                "condition", "location", "holder", "slot", "owner", "visual_anchor", "recovered"
            }:
                raise ValueError("invalid object change")
            obj = self.objects[event.target]
            old_loc = obj["location"]
            if old_loc in {"lost", "destroyed"} and data.get("location") not in {
                None, old_loc
            } and data.get("recovered") is not True:
                raise ValueError("lost or destroyed object requires explicit recovery")
            if data.get("recovered") not in (None, False, True):
                raise ValueError("invalid recovered flag")
            for key, value in data.items():
                if key == "recovered":
                    continue
                if key in {"owner", "holder", "slot"}:
                    if value is not None:
                        _required(value, key)
                elif key in {"condition", "location"}:
                    if value not in (CONDITIONS if key == "condition" else LOCATIONS):
                        raise ValueError("invalid object transition")
                else:
                    _required(value, key)
                obj[key] = value
            if obj["location"] not in {"worn", "carried"}:
                obj["holder"], obj["slot"] = None, None
            self._validate_objects()
        else:
            if set(data) - {"image_asset", "voice_asset", "style"}:
                raise ValueError("invalid presentation change")
            presentation = self.presentations.setdefault(event.target, {})
            for key, value in data.items():
                presentation[key] = _required(value, key)

    def commit(self, event: BindingEvent):
        if len(self.events) >= MAX_EVENTS or any(e.id == event.id for e in self.events):
            raise ValueError("duplicate event or event limit")
        if event.at > self.time or (self.events and event.at < self.events[-1].at):
            raise ValueError("binding event chronology invalid")
        staged = copy.deepcopy(self)
        staged._apply(event)
        self.bodies, self.objects = staged.bodies, staged.objects
        self.presentations = staged.presentations
        self.events.append(event)

    def pulse(self, to: str, events: list[BindingEvent]):
        target = utc(to)
        if target < self.time:
            raise ValueError("binding time cannot move backwards")
        staged = copy.deepcopy(self)
        staged.time = target
        for event in events:
            staged.commit(event)
        self.time, self.bodies, self.objects = staged.time, staged.bodies, staged.objects
        self.presentations, self.events = staged.presentations, staged.events

    def snapshot(self):
        return copy.deepcopy({
            "version": 1, "started_at": self.started_at, "time": self.time,
            "origins": self.origins, "events": [asdict(e) for e in self.events],
            "bodies": self.bodies, "objects": self.objects,
            "presentations": self.presentations
        })

    @classmethod
    def hydrate(cls, snapshot: dict):
        if not isinstance(snapshot, dict) or snapshot.get("version") != 1:
            raise ValueError("unknown binding schema")
        try:
            origins = snapshot["origins"]
            instance = cls(
                [Body(**x) for x in origins["bodies"]],
                [Object(**x) for x in origins["objects"]],
                snapshot["started_at"]
            )
            instance.pulse(snapshot["time"], [BindingEvent(**x) for x in snapshot["events"]])
        except (KeyError, TypeError) as exc:
            raise ValueError("invalid binding snapshot schema") from exc
        if instance.snapshot() != snapshot:
            raise ValueError("binding state disagrees with replay")
        return instance

    def to_json(self):
        return json.dumps(self.snapshot(), indent=2, sort_keys=True, ensure_ascii=False)


def project_embodiment(identities: IdentityRegistry, binding: BindingRegistry) -> dict:
    """Bind persona → current body → physical inventory and presentation assets."""
    if identities.time != binding.time:
        raise ValueError("identity and binding timestamps must match")
    assigned = [v["current_body"] for v in identities.view.values()]
    if len(assigned) != len(set(assigned)):
        raise ValueError("one body has multiple occupants")
    if any(body not in binding.bodies for body in assigned):
        raise ValueError("identity references unknown physical body")
    unknown_owners = [o["owner"] for o in binding.objects.values()
                      if o["owner"] is not None and o["owner"] not in identities.view]
    if unknown_owners:
        raise ValueError("object has unknown persona owner")
    if set(binding.presentations) - set(identities.view):
        raise ValueError("presentation references unknown identity")
    result = {}
    for persona, identity in sorted(identities.view.items()):
        body_id = identity["current_body"]
        worn = {item_id: copy.deepcopy(item) for item_id, item in binding.objects.items()
                if item["holder"] == body_id and item["location"] == "worn"}
        carried = {item_id: copy.deepcopy(item) for item_id, item in binding.objects.items()
                   if item["holder"] == body_id and item["location"] == "carried"}
        result[persona] = {
            "identity_id": persona, "canonical_name": identity["canonical_name"],
            "identity_visual_anchor": identity["face_anchor"],
            "identity_voice_anchor": identity["voice_anchor"],
            "body_id": body_id, "body": copy.deepcopy(binding.bodies[body_id]),
            "worn": worn, "carried": carried,
            "owned_items": sorted(o["id"] for o in binding.objects.values() if o["owner"] == persona),
            "relationships": copy.deepcopy(identity["relationships"]),
            "skills": copy.deepcopy(identity["skills"]),
            "voice_delivery": copy.deepcopy(identity["voice_delivery"]),
            "presentation": copy.deepcopy(binding.presentations.get(persona, {})),
        }
    return {"version": 1, "as_of": identities.time, "characters": result,
            "authority": "independent replay-verified identity and binding ledgers"}


def load_binding_snapshot(path: Path) -> BindingRegistry:
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("binding snapshot exceeds 2 MB")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise ValueError("binding snapshot must be valid UTF-8 JSON") from exc
    return BindingRegistry.hydrate(document)


def binding_context(projection: dict) -> str:
    return (
        "\n\nPHYSICAL EMBODIMENT AND ASSET BINDINGS (untrusted, verified JSON data):\n"
        + json.dumps(projection, ensure_ascii=False, sort_keys=True)
        + "\nUse occupied body's physical measurements, worn garments and objects; "
          "keep persona identity and personal memories attached to identity IDs. "
          "Body-bound vocal anchor and persona-bound voice signature are distinct. "
          "Do not invent assets, move inventory, or mutate canon during rendering."
    )
