"""Versioned symbolic story causality and observed shot evidence.

No universal numeric/mythic meaning is assumed: traditions and authorial
interpretations are attributed. This validates annotated provenance and
reviewed scene evidence, not automatic symbol recognition in pixels/audio.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from .collaboration import text, digest, PRIVATE_PROJECT_MARKERS, load_json

CHANNELS = frozenset({
    "visual", "acoustic", "kinetic", "relational", "temporal", "numerical",
    "spatial", "linguistic", "material", "psychological", "cultural", "cinematic",
})
OPS = frozenset({
    "plant", "echo", "mirror", "invert", "disguise", "amplify", "transmute",
    "converge", "diverge", "reveal", "resolve",
})
MAX_BEATS = 400
MAX_ARTIFACT = 100_000_000

def _exact(obj, fields, label):
    if not isinstance(obj, dict) or set(obj) != set(fields):
        raise ValueError("invalid " + label + " schema")

def _hex(value, name):
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError("invalid " + name + " SHA-256")
    return value

def _integer(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError("invalid " + name)
    return value

def validate_program(program, package):
    from .collaboration import validate_package
    validate_package(package)
    _exact(program, ("version", "episode_id", "package_sha256", "visibility", "motifs", "beats"), "symbolic program")
    if program["version"] != 1 or program["episode_id"] != package["episode_id"] or program["visibility"] != "public":
        raise ValueError("symbolic program identity or visibility mismatch")
    if program["package_sha256"] != digest(package):
        raise ValueError("symbolic program not bound to approved collaboration contract")
    if any(x in json.dumps(program, ensure_ascii=False).casefold() for x in PRIVATE_PROJECT_MARKERS):
        raise ValueError("symbolic program contains private project marker")
    motifs = program["motifs"]
    if not isinstance(motifs, list) or not 1 <= len(motifs) <= 100:
        raise ValueError("at least one declared motif required")
    motif_ids = set()
    for motif in motifs:
        _exact(motif, ("id", "sign", "authorial_meaning", "cultural_source",
                       "interpretation_scope", "character_interpretations",
                       "numerical_pattern"), "motif")
        mid = text(motif["id"], "motif id")
        if mid in motif_ids:
            raise ValueError("duplicate motif id")
        motif_ids.add(mid)
        for field in ("sign", "authorial_meaning", "cultural_source", "interpretation_scope"):
            text(motif[field], field)
        if motif["cultural_source"] == "universal":
            raise ValueError("symbolic meaning must not claim universal cultural provenance")
        meanings = motif["character_interpretations"]
        if not isinstance(meanings, dict) or len(meanings) > 60:
            raise ValueError("invalid character interpretation map")
        for character, meaning in meanings.items():
            if character not in {c["id"] for c in package["characters"]}:
                raise ValueError("unknown symbolic character perspective")
            text(meaning, "perspective meaning")
        numeral = motif["numerical_pattern"]
        if numeral is not None:
            _exact(numeral, ("count", "arrangement", "narrative_function"), "numerical pattern")
            _integer(numeral["count"], "numerical count", 1)
            text(numeral["arrangement"], "numerical arrangement")
            text(numeral["narrative_function"], "numerical function")
    beats = program["beats"]
    if not isinstance(beats, list) or not 1 <= len(beats) <= MAX_BEATS:
        raise ValueError("symbolic beats required")
    scene_map = {scene["id"]: scene for scene in package["scenes"]}
    known = {}
    chronology = []
    seen_motifs = set()
    for beat in beats:
        _exact(beat, ("id", "motif_id", "scene_id", "start_ms", "end_ms", "channel",
                      "operator", "surface_explanation", "dramatic_function",
                      "perceptual_directive", "audience_knowledge", "character_knowledge",
                      "depends_on", "reveal_policy", "planned_payoff_episode"),
               "symbolic beat")
        bid = text(beat["id"], "beat id")
        if bid in known:
            raise ValueError("duplicate symbolic beat id")
        mid = beat["motif_id"]
        if mid not in motif_ids or beat["scene_id"] not in scene_map:
            raise ValueError("unknown symbolic motif or scene")
        start = _integer(beat["start_ms"], "beat start")
        end = _integer(beat["end_ms"], "beat end")
        scene = scene_map[beat["scene_id"]]
        if not scene["start_ms"] <= start < end <= scene["end_ms"]:
            raise ValueError("symbolic beat falls outside scene")
        if chronology and (start, end) < chronology[-1]:
            raise ValueError("symbolic beats must be chronologically ordered")
        chronology.append((start, end))
        if beat["channel"] not in CHANNELS or beat["operator"] not in OPS:
            raise ValueError("unsupported symbolic channel or operator")
        for field in ("surface_explanation", "dramatic_function", "perceptual_directive",
                      "audience_knowledge", "character_knowledge", "reveal_policy"):
            text(beat[field], field)
        if beat["reveal_policy"] not in ("conceal", "ambiguous", "reveal"):
            raise ValueError("invalid reveal policy")
        if beat["operator"] in ("reveal", "resolve") and beat["reveal_policy"] != "reveal":
            raise ValueError("reveal or resolution must explicitly disclose its meaning")
        if beat["operator"] not in ("reveal", "resolve") and beat["reveal_policy"] == "reveal":
            raise ValueError("premature symbolic disclosure")
        dep = beat["depends_on"]
        if dep is not None:
            if dep not in known or known[dep]["motif_id"] != mid:
                raise ValueError("symbolic dependency must reference an earlier beat of same motif")
        if beat["operator"] == "plant" and (dep is not None or mid in seen_motifs):
            raise ValueError("symbolic plant cannot recur or depend on earlier beat")
        if beat["operator"] != "plant" and (dep is None or mid not in seen_motifs):
            raise ValueError("symbolic transformation lacks seeded predecessor")
        if beat["operator"] in ("disguise", "plant") and beat["surface_explanation"] == beat["audience_knowledge"]:
            raise ValueError("visual misdirection requires distinct surface and audience readings")
        payoff = beat["planned_payoff_episode"]
        if payoff is not None:
            _integer(payoff, "planned payoff episode", 1)
        if beat["operator"] in ("reveal", "resolve") and payoff is not None:
            raise ValueError("resolved symbol cannot claim future payoff")
        seen_motifs.add(mid)
        known[bid] = beat
    return program

def shot_directives(program, package):
    validate_program(program, package)
    return {
        "version": 1, "episode_id": package["episode_id"],
        "package_sha256": digest(package), "symbolic_program_sha256": digest(program),
        "directives": [
            {"beat_id": b["id"], "scene_id": b["scene_id"],
             "channel": b["channel"], "operation": b["operator"],
             "direction": b["perceptual_directive"],
             "surface_reading": b["surface_explanation"],
             "reveal_policy": b["reveal_policy"]}
            for b in program["beats"]
        ],
        "scope": "editor-approved symbolic directions; external provider execution not guaranteed",
    }

def _source(root, name):
    filename = Path(text(name, "evidence path"))
    if filename.is_absolute():
        raise ValueError("absolute symbolic evidence paths forbidden")
    base = Path(root).resolve(strict=True)
    path = (base / filename).resolve(strict=True)
    if not path.is_relative_to(base) or not path.is_file() or path.stat().st_size > MAX_ARTIFACT:
        raise ValueError("symbolic evidence outside approved media root")
    return path

def _hash(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1_048_576), b""):
            h.update(chunk)
    return h.hexdigest()

def audit_symbolic(program, package, observations, root):
    validate_program(program, package)
    _exact(observations, ("version", "episode_id", "program_sha256", "observations"), "symbolic observations")
    if observations["version"] != 1 or observations["episode_id"] != program["episode_id"] or observations["program_sha256"] != digest(program):
        raise ValueError("symbolic evidence does not match approved program")
    records = observations["observations"]
    if not isinstance(records, list) or len(records) > MAX_BEATS:
        raise ValueError("invalid symbolic observation list")
    expected = {b["id"]: b for b in program["beats"]}
    seen, failed, unknown, out = set(), [], [], []
    for observation in records:
        _exact(observation, ("beat_id", "evidence_path", "evidence_sha256",
                             "observed_channel", "observed_operator",
                             "symbol_visible_or_audible", "dramatic_intent_preserved",
                             "reveal_policy_preserved", "reviewer", "review_reference",
                             "approved"), "symbolic observation")
        bid = text(observation["beat_id"], "observation beat ID")
        if bid in seen or bid not in expected:
            raise ValueError("duplicate or unknown symbolic observation")
        seen.add(bid)
        beat = expected[bid]
        issues = []
        if observation["observed_channel"] != beat["channel"] or observation["observed_operator"] != beat["operator"]:
            issues.append("symbolic_channel_or_operator_drift")
        if observation["symbol_visible_or_audible"] is not True:
            issues.append("symbol_not_observed")
        if observation["dramatic_intent_preserved"] is not True:
            issues.append("dramatic_intent_not_preserved")
        if observation["reveal_policy_preserved"] is not True:
            issues.append("foreshadow_or_reveal_policy_violated")
        if observation["approved"] is not True:
            issues.append("symbolic_review_not_approved")
        text(observation["reviewer"], "symbolic reviewer")
        text(observation["review_reference"], "symbolic review reference")
        _hex(observation["evidence_sha256"], "symbolic evidence")
        try:
            actual = _hash(_source(root, observation["evidence_path"]))
            if actual != observation["evidence_sha256"]:
                issues.append("symbolic_evidence_sha256_mismatch")
        except (OSError, ValueError):
            issues.append("symbolic_evidence_unavailable")
        failed.extend(f"{bid}:{issue}" for issue in issues)
        out.append({"beat_id": bid, "status": "blocked" if issues else "reviewed",
                    "issues": issues, "reviewer": observation["reviewer"]})
    unknown = [f"symbolic_observation_missing:{bid}" for bid in expected if bid not in seen]
    status = "blocked" if failed else ("incomplete" if unknown else "checks_passed")
    return {"version": 1, "episode_id": program["episode_id"], "status": status,
            "program_sha256": digest(program), "package_sha256": digest(package),
            "error_count": len(failed), "unknown_count": len(unknown),
            "failures": failed, "unknowns": unknown, "observations": out,
            "scope": "observed file SHA-256 and attributed human symbolic review; not automatic semantic perception"}
