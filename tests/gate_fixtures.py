"""Synthetic approved-by-test fixtures; never real cinematic validation."""
import hashlib
import json
from cinemaswarm_world.collaboration import digest, validate_acknowledgment
from cinemaswarm_world.performance import audit_performance

def write_gate(root, episode_id="lantern-01", audio_name="voice.wav"):
    root.mkdir(parents=True, exist_ok=True)
    audio = root / audio_name
    if not audio.exists():
        audio.write_bytes(b"synthetic-audio-not-real-performance")
    sha = hashlib.sha256(audio.read_bytes()).hexdigest()
    package = {
        "version": 1, "project_id": "lantern-city", "episode_id": episode_id,
        "visibility": "public",
        "creative_intent": "Trust is demonstrated by who receives the talisman.",
        "canon": {"snapshot_id": "synthetic-001", "digest": "a"*64,
                  "dramatic_beats": ["Mara transfers trust to Kai."]},
        "characters": [{"id": "mara", "name": "Mara", "visual_anchor": "mara-v1",
                        "voice_anchor": "mara-v1", "voice_id": "approved-voice-mara-v1",
                        "voice_preview_sha256": sha, "voice_approved": True}],
        "relationships": [],
        "scenes": [{"id": "opening", "purpose": "Trust is visible in a decision",
                    "visual_action": "Mara hands a talisman to an ally.",
                    "start_ms": 0, "end_ms": 2000}],
        "dialogue": [{"id": "line-1", "scene_id": "opening", "speaker_id": "mara",
                      "channel": "onscreen", "voice_id": "approved-voice-mara-v1",
                      "visible_character_id": "mara", "start_ms": 100, "end_ms": 900,
                      "text": "Take it."}],
        "provider": {"name": "test-provider",
                     "capabilities": {"structured_planning": False, "voice_binding": False,
                                      "per_character_lipsync": False, "mcp_resources": False}}
    }
    ack = {"package_sha256": digest(package), "provider": "test-provider",
           "understood_scene_ids": ["opening"], "understood_character_ids": ["mara"],
           "unknowns": [], "interpretation": "Mara's decision is visible.",
           "approved_by": "test-editor", "human_approved": True}
    validate_acknowledgment(package, ack)
    takes = {"version": 1, "episode_id": episode_id,
             "takes": [{"dialogue_id": "line-1", "speaker_id": "mara",
                        "voice_id": "approved-voice-mara-v1", "audio_source": audio_name,
                        "audio_sha256": sha, "voice_match_approved": True,
                        "lip_sync_approved": True, "sync_offset_ms": 20,
                        "reviewer": "test-editor", "evidence": "synthetic-test-evidence"}]}
    perf = audit_performance(package, takes, root)
    perf["package_sha256"] = digest(package)
    for filename, payload in (("collaboration.json", package), ("ack.json", ack),
                              ("performance.json", perf), ("takes.json", takes)):
        (root / filename).write_text(json.dumps(payload, indent=2))
    from cinemaswarm_world.symbolic_narrative import audit_symbolic
    program = {
        "version": 1, "episode_id": episode_id, "visibility": "public",
        "package_sha256": digest(package),
        "motifs": [{
            "id": "talisman-gift", "sign": "handing over a talisman",
            "authorial_meaning": "Trust demonstrated through custody",
            "cultural_source": "original screenplay, no borrowed religious meaning",
            "interpretation_scope": "story-specific",
            "character_interpretations": {"mara": "Trust is a deliberate risk"},
            "numerical_pattern": None,
        }],
        "beats": [{
            "id": "plant-trust", "motif_id": "talisman-gift",
            "scene_id": "opening", "start_ms": 100, "end_ms": 900,
            "channel": "visual", "operator": "plant",
            "surface_explanation": "A hand passes an ordinary object",
            "dramatic_function": "Seed a later cost of trust",
            "perceptual_directive": "Hold on the object as it changes hands",
            "audience_knowledge": "The gesture may reveal allegiance",
            "character_knowledge": "Mara believes it is a safe choice",
            "depends_on": None, "reveal_policy": "conceal",
            "planned_payoff_episode": 3,
        }]
    }
    obs = {"version": 1, "episode_id": episode_id, "program_sha256": digest(program),
           "observations": [{
              "beat_id": "plant-trust", "evidence_path": audio_name,
              "evidence_sha256": sha,
              "observed_channel": "visual", "observed_operator": "plant",
              "symbol_visible_or_audible": True,
              "dramatic_intent_preserved": True,
              "reveal_policy_preserved": True,
              "reviewer": "synthetic-test-reviewer",
              "review_reference": "fixture_only_no_real_media",
              "approved": True
           }]}
    symbolic = audit_symbolic(program, package, obs, root)
    for filename, payload in (("symbolic.json", program), ("symbolic-observations.json", obs),
                              ("symbolic-report.json", symbolic)):
        (root / filename).write_text(json.dumps(payload, indent=2))
    return {"collaboration_package": "collaboration.json",
            "collaboration_ack": "ack.json", "performance_report": "performance.json",
            "symbolic_program": "symbolic.json",
            "symbolic_report": "symbolic-report.json"}
