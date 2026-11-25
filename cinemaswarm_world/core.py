"""Deterministic, offline world-state kernel for narrative production.

Symbolic archetypes, astrology, and numerology are author-supplied fiction
metadata, not inferred personality measurements or predictive science.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import copy
import json


def _utc(value: str) -> str:
    """Require timezone-aware ISO timestamp; normalize to UTC."""
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("timestamps must contain a UTC offset")
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass
class Character:
    id: str
    name: str
    instantiated_at: str
    archetypes: list[str] = field(default_factory=list)
    symbolic_profile: dict[str, Any] = field(default_factory=dict)
    motivations: list[str] = field(default_factory=list)
    memories: list[str] = field(default_factory=list)
    relationships: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.name.strip():
            raise ValueError("character id and name are required")
        self.instantiated_at = _utc(self.instantiated_at)


@dataclass(frozen=True)
class Event:
    id: str
    at: str
    actor_id: str
    kind: str
    target_id: str | None = None
    detail: str = ""
    provenance: str = ""

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.actor_id.strip() or not self.kind.strip():
            raise ValueError("event id, actor, and kind are required")
        object.__setattr__(self, "at", _utc(self.at))


class World:
    """Explicit, auditable event ledger; no LLM or rendering side effects."""

    def __init__(self, world_id: str, started_at: str) -> None:
        if not world_id.strip():
            raise ValueError("world id is required")
        self.id = world_id
        self.time = _utc(started_at)
        self.characters: dict[str, Character] = {}
        self.events: list[Event] = []
        self._event_ids: set[str] = set()

    def instantiate(self, character: Character) -> None:
        if character.id in self.characters:
            raise ValueError("duplicate character id")
        if character.instantiated_at > self.time:
            raise ValueError("character instantiation is in the world's future")
        self.characters[character.id] = copy.deepcopy(character)

    def advance(self, to: str) -> None:
        timestamp = _utc(to)
        if timestamp < self.time:
            raise ValueError("world time cannot move backward")
        self.time = timestamp

    def commit(self, event: Event) -> None:
        if event.id in self._event_ids:
            raise ValueError("duplicate event id")
        if event.actor_id not in self.characters:
            raise ValueError("actor must exist")
        if event.target_id is not None and event.target_id not in self.characters:
            raise ValueError("target must exist")
        if event.at > self.time:
            raise ValueError("event is in the future; advance world first")
        if self.events and event.at < self.events[-1].at:
            raise ValueError("events must be committed chronologically")
        if event.at < self.characters[event.actor_id].instantiated_at:
            raise ValueError("event predates actor instantiation")
        if event.target_id and event.at < self.characters[event.target_id].instantiated_at:
            raise ValueError("event predates target instantiation")
        if event.kind not in {"observation", "choice", "conflict", "revelation", "relationship"}:
            raise ValueError("unsupported event kind")
        self.events.append(event)
        self._event_ids.add(event.id)
        if event.detail:
            self.characters[event.actor_id].memories.append(event.detail)
            if event.target_id and event.kind == "relationship":
                self.characters[event.actor_id].relationships[event.target_id] = event.detail

    def pulse(self, to: str, events: list[Event] | None = None) -> dict[str, int]:
        """TCE-inspired cycle: validate origins, sustain state, commit transformations.

        Atomic on validation failure: staged changes never partially mutate this world.
        """
        staged = copy.deepcopy(self)
        staged.advance(to)
        for event in events or []:
            staged.commit(event)
        self.__dict__.update(staged.__dict__)
        return {"origination": len(self.characters), "sustenance": len(self.characters),
                "transformation": len(events or []), "circulation": len(self.events)}

    def snapshot(self) -> dict[str, Any]:
        """Return JSON-safe detached state, suitable for provenance and tests."""
        from dataclasses import asdict
        return copy.deepcopy({
            "world_id": self.id, "time": self.time,
            "characters": {key: asdict(value) for key, value in sorted(self.characters.items())},
            "events": [asdict(event) for event in self.events],
        })

    def narrative_observer(self, limit: int = 5) -> list[dict[str, str]]:
        """Project committed events into factual scene seeds, never fabricate canon."""
        if limit < 0:
            raise ValueError("limit must be nonnegative")
        return [
            {"event_id": event.id, "at": event.at,
             "actor": self.characters[event.actor_id].name,
             "kind": event.kind, "detail": event.detail,
             "provenance": event.provenance}
            for event in self.events[-limit:]
        ] if limit else []

    def to_json(self) -> str:
        return json.dumps(self.snapshot(), indent=2, ensure_ascii=False, sort_keys=True)
