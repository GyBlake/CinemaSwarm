"""Evidence-linked, offline literary ontology extraction from screenplay text.

This deterministic lexical parser emits *review proposals*, not claims of
semantic understanding. The resulting draft is not an approved morphology.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .morphology import validate_story

MAX_SCREENPLAY_BYTES = 1_000_000
MAX_REVIEW_BYTES = 2_000_000

RULES = (
    ("betrayal", r"\b(betray(?:s|ed|al)?|double.cross(?:es|ed)?|sells? (?:out|them))\b"),
    ("revelation", r"\b(discovers?|uncovers?|reveals?|realizes?|finds? out|exposes?)\b"),
    ("reversal", r"\b(reverses?|turns? the tables|overthrows?|changes? sides|upends?)\b"),
    ("choice", r"\b(chooses?|decides?|refuses?|agrees?|vows?|sacrifices?)\b"),
    ("crisis", r"\b(crisis|trapped|cornered|ultimatum|desperate)\b"),
    ("climax", r"\b(confronts?|final battle|showdown|defeats?)\b"),
    ("resolution", r"\b(resolves?|reconciles?|restores?|ends? the conflict)\b"),
    ("inciting_incident", r"\b(disappears?|vanishes?|interrupts?|arrives? unexpectedly)\b"),
    ("obstacle", r"\b(blocks?|prevents?|stops?|denies?|locks? out|fails?)\b"),
    ("escalation", r"\b(escalates?|intensifies?|worsens?|threatens?)\b"),
    ("aftermath", r"\b(afterwards|in the aftermath|later that day)\b"),
)
OUTCOMES = (
    ("sacrifice", r"\b(sacrifices?|gives? up)\b"),
    ("separation", r"\b(separates?|abandons?|leaves?|exiles?)\b"),
    ("discovery", r"\b(discovers?|uncovers?|reveals?|realizes?|finds? out)\b"),
    ("deception", r"\b(betray(?:s|ed|al)?|lies?|deceives?)\b"),
    ("alliance", r"\b(joins?|unites?|allies|alliance)\b"),
    ("loss", r"\b(loses?|lost|vanishes?|disappears?)\b"),
    ("gain", r"\b(gains?|wins?|receives?)\b"),
    ("failure", r"\b(fails?|defeated)\b"),
    ("success", r"\b(succeeds?|restores?|resolves?)\b"),
)
ROLE_DECL = re.compile(r"^ROLE\s+([\w -]{1,70})\s*:\s*(protagonist|antagonist|ally|mentor|rival|ensemble|other)\s*$", re.I)
SCENE_HEADING = re.compile(r"^(?:INT\.|EXT\.|INT/EXT\.|SCENE\s+\d+\b)", re.I)
CAUSE_CUE = re.compile(r"\b(because|therefore|as a result|consequently|in response|so that)\b", re.I)


def _match(text: str, rules: tuple) -> tuple[str, str] | None:
    for label, pattern in rules:
        found = re.search(pattern, text, flags=re.I)
        if found:
            return label, found.group(0)
    return None


def extract_draft(screenplay: str, story_id: str) -> dict:
    """Suggest beats and cite exact source lines; uncertain fields remain visible."""
    if not screenplay.strip():
        raise ValueError("screenplay cannot be empty")
    if len(screenplay.encode("utf-8")) > MAX_SCREENPLAY_BYTES:
        raise ValueError("screenplay exceeds 1 MB")
    if not isinstance(story_id, str) or not story_id.strip() or len(story_id) > 128:
        raise ValueError("story_id must be between 1 and 128 characters")
    roles = {}
    for line in screenplay.splitlines():
        match = ROLE_DECL.match(line.strip())
        if match:
            roles[match.group(1).lower()] = match.group(2).lower()

    beats, evidence = [], []
    scene = "UNSPECIFIED"
    for line_no, raw in enumerate(screenplay.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if SCENE_HEADING.match(line):
            scene = line[:160]
            continue
        if ROLE_DECL.match(line) or line.startswith("#"):
            continue
        # Character labels are not narrative events.
        if line.isupper() and len(line.split()) <= 4:
            continue
        matched = _match(line, RULES)
        if not matched:
            continue
        function, cue = matched
        outcome_match = _match(line, OUTCOMES)
        outcome = outcome_match[0] if outcome_match else "uncertain"
        speakers = [role for name, role in roles.items() if re.search(r"\b" + re.escape(name) + r"\b", line, re.I)]
        role = speakers[0] if len(set(speakers)) == 1 else "other"
        cause = len(beats) - 1 if beats and CAUSE_CUE.search(line) else None
        beats.append({"function": function, "actor_role": role, "outcome": outcome, "cause": cause})
        warnings = ["lexical guess: confirm dramatic function and outcome"]
        if role == "other":
            warnings.append("actor role unresolved")
        if cause is None and beats[:-1]:
            warnings.append("causal predecessor not established")
        if len(set(speakers)) > 1:
            warnings.append("multiple conflicting roles mentioned")
        evidence.append({
            "beat_index": len(beats) - 1, "line": line_no, "scene": scene,
            "excerpt": line[:300], "cue": cue,
            "confidence": "low", "warnings": warnings, "approved": False,
        })
        if len(beats) >= 32:
            break
    return {
        "review_schema": 1,
        "status": "needs_review",
        "candidate": {"version": 1, "story_id": story_id, "beats": beats},
        "evidence": evidence,
        "source_sha256": hashlib.sha256(screenplay.encode("utf-8")).hexdigest(),
        "method": "offline-lexical-cues-v1",
        "notes": "Every beat must be reviewed. Causal links are only guesses; add or correct them manually. No AI provider used.",
    }


def extract_file(path: Path, story_id: str) -> dict:
    if path.stat().st_size > MAX_SCREENPLAY_BYTES:
        raise ValueError("screenplay exceeds 1 MB")
    try:
        source = path.read_text(encoding="utf-8")
    except UnicodeError as exc:
        raise ValueError("screenplay must be UTF-8") from exc
    return extract_draft(source, story_id)


def finalize_review(review: dict) -> dict:
    """Explicitly authorize every beat before handing it to morphology gate."""
    if not isinstance(review, dict) or review.get("review_schema") != 1:
        raise ValueError("unsupported review schema")
    if review.get("status") != "needs_review":
        raise ValueError("expected unfinalized review draft")
    if review.get("method") != "offline-lexical-cues-v1":
        raise ValueError("unknown extraction method")
    source_hash = review.get("source_sha256")
    if not isinstance(source_hash, str) or not re.fullmatch(r"[a-f0-9]{64}", source_hash):
        raise ValueError("invalid source digest")
    candidate, evidence = review.get("candidate"), review.get("evidence")
    if not isinstance(candidate, dict) or not isinstance(evidence, list):
        raise ValueError("missing candidate or evidence")
    beats = candidate.get("beats")
    if not isinstance(beats, list) or len(evidence) != len(beats):
        raise ValueError("each candidate beat needs matching evidence")
    for index, record in enumerate(evidence):
        if not isinstance(record, dict) or record.get("beat_index") != index:
            raise ValueError("invalid beat evidence index")
        if record.get("approved") is not True:
            raise ValueError("every beat requires explicit approved=true")
        if not isinstance(record.get("line"), int) or record["line"] < 1:
            raise ValueError("invalid evidence line")
        if not isinstance(record.get("excerpt"), str) or not record["excerpt"]:
            raise ValueError("missing source excerpt")
    validate_story(candidate)
    # Keep structural data and provenance, but never upgrade suggestions to world canon.
    return {
        **candidate,
        "review_provenance": {"source_sha256": source_hash,
                              "reviewed_beats": len(beats),
                              "method": review["method"]},
    }


def finalize_file(path: Path) -> dict:
    if path.stat().st_size > MAX_REVIEW_BYTES:
        raise ValueError("review exceeds 2 MB")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise ValueError("review must be valid UTF-8 JSON") from exc
    return finalize_review(data)
