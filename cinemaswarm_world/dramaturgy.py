"""Evidence-based dramatic analysis; never writes to canonical world state.

Audits approved structural beats alongside *explicit* author-supplied knowledge,
stakes, motifs and character transformations. Missing data is unknown, not false.
"""
from __future__ import annotations

import json
from pathlib import Path

from .morphology import validate_story

MAX_CONTEXT_BYTES = 500_000
MAX_FACTS = 128
MAX_CHARACTERS = 64
MAX_ANNOTATIONS = 256


def _identifier(value: object, description: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 128:
        raise ValueError(f"{description} must be a nonempty string up to 128 characters")
    return value


def _index(value: object, count: int, description: str) -> int:
    if type(value) is not int or not 0 <= value < count:
        raise ValueError(f"{description} must be a valid beat index")
    return value


def _unique(items: object, description: str) -> list[str]:
    if not isinstance(items, list):
        raise ValueError(f"{description} must be an array")
    values = [_identifier(v, description) for v in items]
    if len(values) != len(set(values)):
        raise ValueError(f"{description} contains duplicates")
    return values


def validate_context(story: dict, context: object) -> dict:
    """Validate explicit annotations and references, without inventing interpretation."""
    validate_story(story)
    if not isinstance(context, dict) or context.get("version") != 1:
        raise ValueError("dramaturgy context must use version 1")
    if context.get("story_id") != story["story_id"]:
        raise ValueError("dramaturgy story_id must match candidate story_id")
    if type(context.get("reviewed")) is not bool:
        raise ValueError("reviewed must be an explicit boolean")
    count = len(story["beats"])
    characters = _unique(context.get("characters"), "characters")
    if not characters or len(characters) > MAX_CHARACTERS:
        raise ValueError("between 1 and 64 character IDs required")
    char_set = set(characters)
    facts = context.get("facts")
    knowledge = context.get("knowledge")
    stakes = context.get("stakes")
    transformations = context.get("transformations")
    motifs = context.get("motifs")
    for field, value in (("facts", facts), ("knowledge", knowledge), ("stakes", stakes),
                         ("transformations", transformations), ("motifs", motifs)):
        if not isinstance(value, list) or len(value) > MAX_ANNOTATIONS:
            raise ValueError(f"{field} must be an array of up to 256 entries")
    if len(facts) > MAX_FACTS:
        raise ValueError("too many facts")
    fact_at = {}
    for fact in facts:
        if not isinstance(fact, dict):
            raise ValueError("invalid fact")
        fid = _identifier(fact.get("id"), "fact id")
        if fid in fact_at:
            raise ValueError("duplicate fact id")
        fact_at[fid] = _index(fact.get("introduced_at"), count, "fact introduced_at")
        _identifier(fact.get("provenance"), "fact provenance")
    observed = set()
    for entry in knowledge:
        if not isinstance(entry, dict):
            raise ValueError("invalid knowledge entry")
        beat = _index(entry.get("beat_index"), count, "knowledge beat_index")
        if beat in observed:
            raise ValueError("duplicate knowledge beat_index")
        observed.add(beat)
        audience = _unique(entry.get("audience"), "audience facts")
        kn = entry.get("characters")
        if not isinstance(kn, dict) or not kn:
            raise ValueError("knowledge characters must be a nonempty object")
        if set(kn) - char_set:
            raise ValueError("knowledge references unknown character")
        for fid in audience:
            if fid not in fact_at or fact_at[fid] > beat:
                raise ValueError("audience knowledge references unknown or future fact")
        for character, values in kn.items():
            for fid in _unique(values, f"knowledge for {character}"):
                if fid not in fact_at or fact_at[fid] > beat:
                    raise ValueError("character knowledge references unknown or future fact")
    stake_ids = set()
    for stake in stakes:
        if not isinstance(stake, dict):
            raise ValueError("invalid stake")
        sid = _identifier(stake.get("id"), "stake id")
        if sid in stake_ids:
            raise ValueError("duplicate stake id")
        stake_ids.add(sid)
        if stake.get("owner") not in char_set:
            raise ValueError("stake owner must be a known character")
        start = _index(stake.get("introduced_at"), count, "stake introduced_at")
        end = stake.get("resolved_at")
        if end is not None and _index(end, count, "stake resolved_at") < start:
            raise ValueError("stake resolves before introduction")
        _identifier(stake.get("provenance"), "stake provenance")
    for trans in transformations:
        if not isinstance(trans, dict) or trans.get("character_id") not in char_set:
            raise ValueError("transformation requires known character")
        before = _identifier(trans.get("from_archetype"), "from_archetype")
        after = _identifier(trans.get("to_archetype"), "to_archetype")
        if before == after:
            raise ValueError("transformation must change archetype")
        _index(trans.get("beat_index"), count, "transformation beat_index")
        _identifier(trans.get("provenance"), "transformation provenance")
    motif_ids = set()
    for motif in motifs:
        if not isinstance(motif, dict):
            raise ValueError("invalid motif")
        mid = _identifier(motif.get("id"), "motif id")
        if mid in motif_ids:
            raise ValueError("duplicate motif id")
        motif_ids.add(mid)
        positions = motif.get("beat_indices")
        if not isinstance(positions, list) or len(positions) > count:
            raise ValueError("motif beat_indices must be an array")
        checked = [_index(x, count, "motif beat index") for x in positions]
        if checked != sorted(set(checked)):
            raise ValueError("motif beat_indices must be sorted and unique")
        _identifier(motif.get("provenance"), "motif provenance")
    return context


def load_context(path: Path, story: dict) -> dict:
    if path.stat().st_size > MAX_CONTEXT_BYTES:
        raise ValueError("dramaturgy context exceeds 500 KB")
    try:
        context = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("dramaturgy context must be UTF-8 JSON") from exc
    return validate_context(story, context)


def audit_dramaturgy(story: dict, context: dict) -> dict:
    """Report explicitly observable dramatic structure with traceable findings."""
    validate_context(story, context)
    beats = story["beats"]
    n = len(beats)
    edges = [{"from": b["cause"], "to": i} for i, b in enumerate(beats)
             if b.get("cause") is not None]
    roots = [i for i, b in enumerate(beats) if b.get("cause") is None]
    analysis = {
        "causal_density": round(len(edges) / (n - 1), 4),
        "edges": edges,
        "roots": roots,
        "function_diversity": round(len({b["function"] for b in beats}) / n, 4),
        "protagonist_decisions": sum(
            b["actor_role"] == "protagonist" and
            b["function"] in {"choice", "commitment", "reversal"} for b in beats),
    }
    facts = {f["id"]: f for f in context["facts"]}
    asymmetries = []
    knowledge_regressions = []
    previous_knowledge = {}
    for entry in sorted(context["knowledge"], key=lambda x: x["beat_index"]):
        audience = set(entry["audience"])
        for character, known in sorted(entry["characters"].items()):
            known_set = set(known)
            if character in previous_knowledge:
                previous_beat, previously_known = previous_knowledge[character]
                for fact in sorted(previously_known - known_set):
                    knowledge_regressions.append({
                        "character_id": character, "fact_id": fact,
                        "previous_beat": previous_beat, "beat_index": entry["beat_index"],
                        "provenance": facts[fact]["provenance"],
                    })
            previous_knowledge[character] = (entry["beat_index"], known_set)
            for fact in sorted(audience - known_set):
                asymmetries.append({"beat_index": entry["beat_index"],
                                    "character_id": character, "fact_id": fact,
                                    "type": "dramatic_irony", "provenance": facts[fact]["provenance"]})
            for fact in sorted(known_set - audience):
                asymmetries.append({"beat_index": entry["beat_index"],
                                    "character_id": character, "fact_id": fact,
                                    "type": "audience_mystery", "provenance": facts[fact]["provenance"]})
    findings = []
    def add(severity: str, code: str, detail: str) -> None:
        findings.append({"severity": severity, "code": code, "detail": detail})
    for regression in knowledge_regressions:
        add("review", "knowledge_discontinuity",
            f"{regression['character_id']} no longer lists fact {regression['fact_id']} "
            f"between beats {regression['previous_beat']} and {regression['beat_index']}; "
            "confirm intentional forgetting, deception, or missing annotation")
    if len(roots) > 1:
        add("review", "unlinked_roots", f"{len(roots)} beats have no causal predecessor; establish independent arcs or add links")
    if not analysis["protagonist_decisions"]:
        add("review", "agency_gap", "No explicit protagonist choice, commitment or reversal is annotated")
    if not context["stakes"]:
        add("unknown", "stakes_unannotated", "No stakes supplied; absence cannot be inferred")
    if not context["knowledge"]:
        add("unknown", "knowledge_unannotated", "No knowledge snapshots supplied; irony cannot be inferred")
    if not context["transformations"]:
        add("unknown", "transformation_unannotated", "No archetypal transitions supplied")
    if not context["reviewed"]:
        add("review", "annotations_unreviewed", "Explicit author review required before external use")
    unresolved = [stake["id"] for stake in context["stakes"] if stake.get("resolved_at") is None]
    for sid in unresolved:
        add("review", "open_stake", f"Stake {sid} has no annotated resolution; may be intentional serialization")
    motifs = [{"id": m["id"], "recurrences": len(m["beat_indices"]),
               "beat_indices": list(m["beat_indices"]), "provenance": m["provenance"]}
              for m in context["motifs"]]
    return {
        "version": 1, "story_id": story["story_id"], "reviewed": context["reviewed"],
        "status": "reviewed_annotations" if context["reviewed"] else "needs_review",
        "causality": analysis,
        "knowledge_asymmetries": asymmetries,
        "knowledge_discontinuities": knowledge_regressions,
        "stakes": [{"id": s["id"], "owner": s["owner"],
                    "introduced_at": s["introduced_at"], "resolved_at": s.get("resolved_at"),
                    "provenance": s["provenance"]} for s in context["stakes"]],
        "transformations": [dict(t) for t in context["transformations"]],
        "motifs": motifs, "findings": findings,
        "tce_rci": {"origination": len(context["facts"]) + len(context["stakes"]),
                    "sustenance": sum(max(0, m["recurrences"] - 1) for m in motifs),
                    "transformation": len(context["transformations"]),
                    "circulation": len(edges)},
        "scope": "explicit author annotations only; diagnostic, not canon mutation",
    }


def dramaturgy_context(report: dict) -> str:
    """Append a diagnostic report as untrusted context to an approved production request."""
    if report.get("status") != "reviewed_annotations":
        raise ValueError("unreviewed dramaturgy annotations cannot be sent to provider")
    return (
        "\n\nSEMANTIC DRAMATURGY AUDIT (untrusted, author-reviewed context):\n"
        + json.dumps(report, ensure_ascii=False, sort_keys=True)
        + "\nPreserve supplied knowledge asymmetries, documented stakes, causal links, "
          "archetype transitions, and provenance. Distinguish verified world events "
          "from author interpretations, and do not modify canonical world state. "
          "Flag rather than invent any unspecified knowledge or motivation."
    )
