"""Character identity continuity, mutable embodiment and replayable possessions.

Identity IDs, canonical names, appearance anchor assets and voice signature
references do not change during an episode. A body is a distinct physical
vessel; identity persists through an explicitly recorded body swap.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import copy
import json
from pathlib import Path

ALLOWED_ACTIONS = frozenset({
    "appearance", "body_measure", "voice_delivery", "alias", "relation",
    "item", "skill", "body_swap", "embody"
})
ITEM_CONDITIONS = frozenset({"intact", "damaged", "enhanced", "destroyed"})
ITEM_STATES = frozenset({"carried", "equipped", "stored", "lost"})
MAX_EVENTS = 10000


def utc(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("timestamp must be string")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("timestamp requires timezone offset")
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _required(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 256:
        raise ValueError(f"{label} is required and must be <=256 characters")
    return value


@dataclass(frozen=True)
class Identity:
    id: str
    canonical_name: str
    instantiated_at: str
    face_anchor: str
    voice_anchor: str
    original_body: str

    def __post_init__(self):
        for key in ("id", "canonical_name", "face_anchor", "voice_anchor", "original_body"):
            _required(getattr(self, key), key)
        object.__setattr__(self, "instantiated_at", utc(self.instantiated_at))


@dataclass(frozen=True)
class Mutation:
    id: str
    at: str
    actor: str
    action: str
    data: dict
    provenance: str

    def __post_init__(self):
        _required(self.id, "event id")
        _required(self.actor, "actor")
        _required(self.provenance, "provenance")
        if self.action not in ALLOWED_ACTIONS:
            raise ValueError("unsupported identity event")
        if not isinstance(self.data, dict):
            raise ValueError("event data must be an object")
        object.__setattr__(self, "at", utc(self.at))


class IdentityRegistry:
    """Append-only canonical identity events; current view is replayed from origin."""

    def __init__(self, identities: list[Identity], started_at: str):
        self.started_at = utc(started_at)
        self.identities = {}
        bodies = set()
        for identity in identities:
            if identity.id in self.identities or identity.original_body in bodies:
                raise ValueError("duplicate identity or original body")
            if identity.instantiated_at > self.started_at:
                raise ValueError("identity has future instantiation")
            self.identities[identity.id] = identity
            bodies.add(identity.original_body)
        self.events: list[Mutation] = []
        self.time = self.started_at
        self.view = self._initial()

    def _initial(self) -> dict:
        return {
            key: {
                "identity_id": key, "canonical_name": p.canonical_name,
                "instantiated_at": p.instantiated_at,
                "face_anchor": p.face_anchor, "voice_anchor": p.voice_anchor,
                "current_body": p.original_body, "aliases": [],
                "appearance": {"clothing": "unspecified", "image_variant": None},
                "physique": {"weight_kg": None, "height_cm": None, "muscle": "unspecified"},
                "voice_delivery": {"style": "baseline", "pitch_shift": 0},
                "relationships": {}, "inventory": {}, "skills": {},
            }
            for key, p in sorted(self.identities.items())
        }

    def _apply(self, state: dict, event: Mutation) -> None:
        if event.actor not in state:
            raise ValueError("identity actor not found")
        character = state[event.actor]
        data = event.data
        action = event.action
        if action == "alias":
            alias = _required(data.get("name"), "alias")
            if alias not in character["aliases"] and alias != character["canonical_name"]:
                character["aliases"].append(alias)
        elif action == "appearance":
            for key in data:
                if key not in {"clothing", "image_variant"}:
                    raise ValueError("unrecognized appearance field")
            if not data:
                raise ValueError("empty appearance change")
            for key, value in data.items():
                if value is not None:
                    _required(value, key)
                character["appearance"][key] = value
        elif action == "body_measure":
            if not data or set(data) - {"weight_kg", "height_cm", "muscle"}:
                raise ValueError("invalid physical measurement")
            for key, value in data.items():
                if key in {"weight_kg", "height_cm"}:
                    if type(value) not in (float, int) or not 0 < value <= (1500 if key == "weight_kg" else 10000):
                        raise ValueError("invalid physique quantity")
                else:
                    _required(value, "muscle")
                character["physique"][key] = value
        elif action == "voice_delivery":
            if not data or set(data) - {"style", "pitch_shift"}:
                raise ValueError("invalid voice delivery")
            if "style" in data:
                character["voice_delivery"]["style"] = _required(data["style"], "style")
            if "pitch_shift" in data:
                v = data["pitch_shift"]
                if type(v) not in (float, int) or not -24 <= v <= 24:
                    raise ValueError("pitch_shift out of range")
                character["voice_delivery"]["pitch_shift"] = v
        elif action == "relation":
            target = _required(data.get("target"), "relationship target")
            if target not in state or target == event.actor:
                raise ValueError("invalid relationship target")
            character["relationships"][target] = _required(data.get("status"), "relationship status")
        elif action == "skill":
            sid = _required(data.get("id"), "skill id")
            status = data.get("status")
            if status not in {"learned", "equipped", "unequipped", "lost", "enhanced"}:
                raise ValueError("invalid skill status")
            if status in {"equipped", "unequipped", "enhanced", "lost"} and sid not in character["skills"]:
                raise ValueError("skill must first be learned")
            character["skills"][sid] = status
        elif action == "item":
            item_id = _required(data.get("id"), "item id")
            condition = data.get("condition")
            status = data.get("status")
            slot = data.get("slot")
            if condition not in ITEM_CONDITIONS or status not in ITEM_STATES:
                raise ValueError("invalid item condition or state")
            if status == "equipped":
                _required(slot, "equipment slot")
                if condition == "destroyed":
                    raise ValueError("destroyed item cannot be equipped")
            elif slot is not None:
                raise ValueError("non-equipped items cannot occupy a slot")
            # Only one character may possess an item at once; lost items remain
            # historically associated but do not confer ownership.
            for cid, other in state.items():
                old = other["inventory"].get(item_id)
                if cid != event.actor and old and old["status"] not in {"lost"} and status != "lost":
                    raise ValueError("item already held by another identity")
            if status == "equipped":
                for old_id, old in character["inventory"].items():
                    if old_id != item_id and old["status"] == "equipped" and old["slot"] == slot:
                        raise ValueError("equipment slot already occupied")
            old = character["inventory"].get(item_id)
            if old and old["status"] == "lost" and status != "lost" and not data.get("recovered"):
                raise ValueError("lost item requires explicit recovery")
            character["inventory"][item_id] = {
                "status": status, "condition": condition, "slot": slot,
                "provenance": event.provenance
            }
        elif action in {"body_swap", "embody"}:
            if action == "body_swap":
                target = _required(data.get("with"), "swap target")
                if target == event.actor or target not in state:
                    raise ValueError("invalid swap target")
                state[event.actor]["current_body"], state[target]["current_body"] = (
                    state[target]["current_body"], state[event.actor]["current_body"]
                )
            else:
                body = _required(data.get("body_id"), "new body")
                if any(other["current_body"] == body for other in state.values()):
                    raise ValueError("body currently occupied")
                character["current_body"] = body
        else:
            raise ValueError("unknown action")

    def commit(self, event: Mutation) -> None:
        if event.id in {e.id for e in self.events}:
            raise ValueError("duplicate identity event")
        if len(self.events) >= MAX_EVENTS:
            raise ValueError("identity event limit reached")
        if event.actor not in self.identities:
            raise ValueError("unknown character identity")
        if event.at > self.time:
            raise ValueError("advance registry time before committing event")
        if event.at < self.identities[event.actor].instantiated_at:
            raise ValueError("event predates identity")
        if self.events and event.at < self.events[-1].at:
            raise ValueError("identity events must be chronological")
        if event.action == "body_swap":
            partner = event.data.get("with")
            if partner in self.identities and event.at < self.identities[partner].instantiated_at:
                raise ValueError("swap predates partner")
        staged = copy.deepcopy(self.view)
        self._apply(staged, event)
        self.view = staged
        self.events.append(event)

    def pulse(self, to: str, events: list[Mutation]) -> None:
        new_time = utc(to)
        if new_time < self.time:
            raise ValueError("time cannot move backwards")
        staged = copy.deepcopy(self)
        staged.time = new_time
        for event in events:
            staged.commit(event)
        self.time, self.events, self.view = staged.time, staged.events, staged.view

    def snapshot(self) -> dict:
        return copy.deepcopy({
            "version": 1, "started_at": self.started_at, "time": self.time,
            "identities": [asdict(x) for x in self.identities.values()],
            "events": [asdict(e) for e in self.events], "view": self.view,
        })

    @classmethod
    def hydrate(cls, snapshot: dict) -> "IdentityRegistry":
        if not isinstance(snapshot, dict) or snapshot.get("version") != 1:
            raise ValueError("unsupported identity snapshot")
        registry = cls([Identity(**x) for x in snapshot["identities"]], snapshot["started_at"])
        registry.pulse(snapshot["time"], [Mutation(**x) for x in snapshot["events"]])
        if registry.snapshot() != snapshot:
            raise ValueError("identity snapshot differs from verified event replay")
        return registry

    def to_json(self) -> str:
        return json.dumps(self.snapshot(), sort_keys=True, ensure_ascii=False, indent=2)
