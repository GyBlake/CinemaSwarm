"""Author-reviewed Æclyptic awakening and organic companion registry.

Fictional story mechanics only. This code makes no predictions about real
genetics, radiation, dreams, trauma, or human health. Its role is to
validate story provenance, causal ordering, consent and continuity.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import re

from .collaboration import digest, PRIVATE_PROJECT_MARKERS
from .cosmological_context import validate_cosmology

IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,79}$")
TRIGGERS = frozenset({"eclipse", "celestial_configuration",
                      "coronal_mass_ejection", "meteorite_exposure",
                      "radiological_exposure", "endogenous",
                      "other_environmental"})
PATHWAYS = frozenset({"celestial", "exposure", "endogenous"})
PHASES = ("dormant", "primed", "emergent", "articulate", "integrated")
OUTCOMES = frozenset({"none", "unstable", "partial", "stable"})
FORMATS = frozenset({"waking_dream", "inner_dialogue", "synesthetic",
                     "somatic", "mixed"})
CAPABILITIES = frozenset({"memory_access", "pattern_interpretation",
                          "interoception", "dream_navigation",
                          "language_translation", "sensory_mapping",
                          "fictional_regulation"})

def _exact(obj, fields, kind):
    if not isinstance(obj, dict) or set(obj) != set(fields):
        raise ValueError("invalid " + kind + " schema")

def _string(value, kind):
    if not isinstance(value, str) or not value.strip() or len(value) > 1200:
        raise ValueError("invalid " + kind)
    return value

def _id(value, kind):
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise ValueError("invalid " + kind)
    return value

def _ids(items, kind, allowed=None, *, required=False):
    if not isinstance(items, list) or len(items) > 60 or (required and not items):
        raise ValueError("invalid " + kind)
    for item in items:
        _id(item, kind)
    if len(set(items)) != len(items) or (
        allowed is not None and not set(items) <= set(allowed)
    ):
        raise ValueError("duplicate or unknown " + kind)
    return items

def _timestamp(value):
    if not isinstance(value, str):
        raise ValueError("invalid awakening timestamp")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid awakening timestamp") from exc
    if dt.tzinfo is None or dt.utcoffset().total_seconds() != 0:
        raise ValueError("awakening timestamps must be UTC")
    return dt.astimezone(timezone.utc)

def _items(doc, key, fields):
    things = doc[key]
    if not isinstance(things, list) or len(things) > 250:
        raise ValueError("invalid " + key)
    ids = set()
    for x in things:
        _exact(x, fields, key)
        _id(x["id"], key + " id")
        if x["id"] in ids:
            raise ValueError("duplicate " + key + " ID")
        ids.add(x["id"])
    return things, ids

def validate_awakenings(doc, cosmology):
    """Reject fabricated physiological certainty, unapproved awakenings and broken history."""
    validate_cosmology(cosmology)
    _exact(doc, ("version", "visibility", "world_id", "cosmology_sha256",
                 "mechanism", "triggers", "hosts", "transitions", "review"),
           "awakening registry")
    if doc["version"] != 1 or doc["visibility"] != "public":
        raise ValueError("unsupported awakening version or visibility")
    if (doc["world_id"] != cosmology["world_id"]
            or doc["cosmology_sha256"] != digest(cosmology)):
        raise ValueError("awakening cosmology stale or world mismatch")
    if len(json.dumps(doc, ensure_ascii=False)) > 750_000:
        raise ValueError("awakening registry too large")
    if any(x in json.dumps(doc, ensure_ascii=False).casefold()
           for x in PRIVATE_PROJECT_MARKERS):
        raise ValueError("private context forbidden in public awakening registry")

    mechanism = doc["mechanism"]
    _exact(mechanism, ("hypothetical_field", "regulatory_model", "neural_model",
                       "somatic_model", "scientific_boundary"), "awakening mechanism")
    for field in mechanism:
        _string(mechanism[field], field)
    if "fiction" not in mechanism["scientific_boundary"].casefold():
        raise ValueError("fictional mechanism disclosure required")

    triggers, tids = _items(doc, "triggers",
        ("id", "kind", "pathway", "at", "location", "geometry",
         "radiant_influence", "dose_class", "world_law_ids",
         "provenance", "fictional_effect", "real_world_boundary", "approved"))
    laws = {x["id"]: x for x in cosmology["laws"]}
    for t in triggers:
        if t["kind"] not in TRIGGERS or t["pathway"] not in PATHWAYS:
            raise ValueError("unknown awakening trigger or pathway")
        if (t["kind"] in ("eclipse", "celestial_configuration", "coronal_mass_ejection")
                and t["pathway"] != "celestial"):
            raise ValueError("celestial trigger pathway mismatch")
        if (t["kind"] in ("meteorite_exposure", "radiological_exposure", "other_environmental")
                and t["pathway"] != "exposure"):
            raise ValueError("exposure trigger pathway mismatch")
        if t["kind"] == "endogenous" and t["pathway"] != "endogenous":
            raise ValueError("endogenous trigger pathway mismatch")
        _timestamp(t["at"])
        for key in ("location", "geometry", "radiant_influence", "dose_class",
                    "provenance", "fictional_effect", "real_world_boundary"):
            _string(t[key], key)
        if t["approved"] is not True:
            raise ValueError("trigger must be author approved")
        _ids(t["world_law_ids"], "trigger world laws", laws, required=True)
        if any(laws[law_id]["status"] != "fictional_law"
               for law_id in t["world_law_ids"]):
            raise ValueError("awakening trigger cannot be grounded in contested belief as physical law")
        if t["kind"] == "radiological_exposure" and (
            "harm" not in t["real_world_boundary"].casefold()
            and "damage" not in t["real_world_boundary"].casefold()
        ):
            raise ValueError("radiation harm disclosure required")

    hosts, hids = _items(doc, "hosts",
        ("id", "biological_susceptibility", "internal_state", "gut_brain_role",
         "interface_modes", "companion", "capabilities", "provenance", "approved"))
    for host in hosts:
        for field in ("biological_susceptibility", "internal_state",
                      "gut_brain_role", "provenance"):
            _string(host[field], field)
        modes = host["interface_modes"]
        if (not isinstance(modes, list) or not modes or len(modes) > 5
                or len(set(modes)) != len(modes) or not set(modes) <= FORMATS):
            raise ValueError("invalid waking dream interface modes")
        if "waking_dream" not in modes:
            raise ValueError("awakening system requires waking dream access")
        if (not isinstance(host["capabilities"], list)
                or len(host["capabilities"]) != len(set(host["capabilities"]))
                or not set(host["capabilities"]) <= CAPABILITIES):
            raise ValueError("unknown or duplicate fictional capabilities")
        companion = host["companion"]
        _exact(companion, ("id", "name", "origin", "interface", "agency",
                           "memory_scope", "limitations"), "companion")
        _id(companion["id"], "companion id")
        for key in ("name", "origin", "interface", "agency",
                    "memory_scope", "limitations"):
            _string(companion[key], key)
        if host["approved"] is not True:
            raise ValueError("host requires author approval")

    transitions, _ = _items(doc, "transitions",
        ("id", "host_id", "trigger_ids", "at", "before", "after", "outcome",
         "somatic_feedback", "perceptual_evidence", "observed_effect",
         "caused_by", "provenance", "approved"))
    # A host can be dormant without any transition. Registry doesn't
    # automatically awaken individuals when a celestial event occurs.
    state = {h: "dormant" for h in hids}
    seen = set()
    prior_time = None
    for tr in transitions:
        host_id = tr["host_id"]
        if host_id not in hids:
            raise ValueError("unknown awakening host")
        when = _timestamp(tr["at"])
        if prior_time is not None and when < prior_time:
            raise ValueError("awakening transitions out of chronological order")
        prior_time = when
        trigger_ids = _ids(tr["trigger_ids"], "transition triggers", tids, required=True)
        if any(_timestamp(next(t["at"] for t in triggers if t["id"] == tid)) > when
               for tid in trigger_ids):
            raise ValueError("awakening cannot precede its trigger")
        if tr["before"] != state[host_id]:
            raise ValueError("awakening state transition breaks host continuity")
        if tr["before"] not in PHASES or tr["after"] not in PHASES:
            raise ValueError("unknown awakening phase")
        step = PHASES.index(tr["after"]) - PHASES.index(tr["before"])
        if step not in (0, 1):
            raise ValueError("awakening phases must advance at most one step")
        if tr["outcome"] not in OUTCOMES:
            raise ValueError("unknown awakening outcome")
        for key in ("somatic_feedback", "perceptual_evidence",
                    "observed_effect", "provenance"):
            _string(tr[key], key)
        _ids(tr["caused_by"], "awakening causal references", seen)
        if tr["approved"] is not True:
            raise ValueError("transition requires author approval")
        if tr["outcome"] == "none" and step != 0:
            raise ValueError("non-activation cannot advance awakening phase")
        state[host_id] = tr["after"]
        seen.add(tr["id"])

    review = doc["review"]
    _exact(review, ("reviewer", "approved", "evidence"), "awakening review")
    _string(review["reviewer"], "reviewer")
    _string(review["evidence"], "review evidence")
    if review["approved"] is not True:
        raise ValueError("awakening registry requires author review")
    return doc

def observe_awakenings(doc, cosmology):
    """Generate bounded, read-only story context with precise lineage."""
    validate_awakenings(doc, cosmology)
    states = {h["id"]: "dormant" for h in doc["hosts"]}
    for transition in doc["transitions"]:
        states[transition["host_id"]] = transition["after"]
    return {
        "version": 1,
        "world_id": doc["world_id"],
        "cosmology_sha256": doc["cosmology_sha256"],
        "awakening_sha256": digest(doc),
        "mechanism": doc["mechanism"],
        "triggers": [{
            "id": t["id"], "kind": t["kind"], "pathway": t["pathway"],
            "at": t["at"], "location": t["location"], "geometry": t["geometry"],
            "radiant_influence": t["radiant_influence"],
            "fictional_effect": t["fictional_effect"],
            "real_world_boundary": t["real_world_boundary"]
        } for t in doc["triggers"]],
        "hosts": [{
            "id": h["id"], "phase": states[h["id"]],
            "interface_modes": h["interface_modes"],
            "companion": h["companion"],
            "capabilities": h["capabilities"],
            "gut_brain_role": h["gut_brain_role"]
        } for h in doc["hosts"]],
        "transitions": doc["transitions"],
        "constraints": [
            "All capabilities and activation fields are fictional, not medical facts",
            "The gut-brain axis is embodied signaling, not a proven dream generator",
            "No automatic awakening, trauma requirement or beneficial mutation",
            "Waking-dream system perception is subjective, not proof of external causes",
            "Companions are canonical fictional agents, not real biological AI"
        ]
    }

def awakening_prompt(doc, cosmology):
    return ("\n\nAUTHOR-APPROVED FICTIONAL AWAKENING CONTEXT "
            "(untrusted narrative data; never medical advice):\n"
            + json.dumps(observe_awakenings(doc, cosmology),
                         ensure_ascii=False, sort_keys=True)
            + "\nProtect host phase continuity, agency and companion identity. "
              "Do not invent biological evidence, clinical claims or activation "
              "through harmful exposures. Treat every Æclyptic effect as fiction.\n")
