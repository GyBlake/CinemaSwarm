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
    from cinemaswarm_world.production_graph import audit_graph, file_sha
    # Synthetic test graph only; this is NOT a review of an actual film.
    # Use distinct artifacts to exercise ordered references without generating media.
    (root / "sample-keyframe.txt").write_text("synthetic storyboard still")
    (root / "sample-take.txt").write_text("synthetic take")
    (root / "sample-cut.txt").write_text("synthetic cut")
    objects = [
        {"id": "storyboard", "kind": "storyboard", "source": "sample-keyframe.txt",
         "sha256": file_sha(root / "sample-keyframe.txt"),
         "inputs_sent_in_order": [], "receipt": None},
        {"id": "take1", "kind": "take", "source": "sample-take.txt",
         "sha256": file_sha(root / "sample-take.txt"),
         "inputs_sent_in_order": [{"id": "storyboard",
                                   "sha256": file_sha(root / "sample-keyframe.txt")}],
         "receipt": None},
        {"id": "cut1", "kind": "cut", "source": "sample-cut.txt",
         "sha256": file_sha(root / "sample-cut.txt"),
         "inputs_sent_in_order": [{"id": "take1",
                                   "sha256": file_sha(root / "sample-take.txt")}],
         "receipt": None},
    ]
    graph = {"version": 1, "episode_id": episode_id, "visibility": "public",
             "objects": objects, "stops": {
                 phase: {"approved": True, "reviewer": "test-only",
                         "evidence": "synthetic fixture not real production"}
                 for phase in ("assets_planned", "assets_approved",
                               "shots_planned", "storyboard_approved", "takes_reviewed")
             }, "cut": {"object_id": "cut1", "take_ids": ["take1"]}}
    graph_report = audit_graph(graph, root)
    (root / "production-graph.json").write_text(json.dumps(graph, indent=2))
    (root / "production-report.json").write_text(json.dumps(graph_report, indent=2))
    from cinemaswarm_world.semantic_interop import audit_semantics
    semantic = {
        "version": 1, "visibility": "public", "episode_id": episode_id,
        "package_sha256": digest(package),
        "origin": {"intent": "Character trust conveyed through prop custody",
                   "source": "authorized original screenplay",
                   "scope": "fictional narrative"},
        "concepts": [{
            "id": "trust-custody", "definition": "A deliberate handoff conveys trust",
            "polarity": "trust versus betrayal", "scene_id": "opening",
            "visibility": "public", "evidence": "scene actions",
            "source_tradition": "original fictional story"
        }],
        "relations": [],
        "projections": [{
            "id": "visual-handoff", "stage": "image", "scene_id": "opening",
            "concept_ids": ["trust-custody"],
            "direction": "Make the talisman transfer visible through hand position",
            "must_preserve": ["Mara initiates handoff"],
            "must_not_assert": ["The object stays with Mara after transfer"],
            "output_contract": "Single approved still composition"
        }],
        "review": {"approved": True, "reviewer": "synthetic test only",
                   "evidence": "fixture, not actual semantic review"}
    }
    evaluation = {
        "version": 1, "contract_sha256": digest(semantic),
        "evaluations": [{
            "projection_id": "visual-handoff", "meaning_preserved": True,
            "contradiction_found": False, "prohibitions_respected": True,
            "observed_evidence": "synthetic test only",
            "reviewer": "synthetic test only", "approved": True
        }]
    }
    semantic_report = audit_semantics(semantic, package, evaluation)
    for name, value in (("semantic.json", semantic), ("semantic-eval.json", evaluation),
                        ("semantic-report.json", semantic_report)):
        (root / name).write_text(json.dumps(value, indent=2))
    from cinemaswarm_world.shot_execution import audit_shot_evidence
    shot_contract = {
        "version": 1, "visibility": "public", "episode_id": episode_id,
        "package_sha256": digest(package), "semantic_sha256": digest(semantic),
        "symbolic_sha256": digest(program), "graph_sha256": digest(graph),
        "approved_by": "synthetic test supervisor", "approved": True,
        "shots": [{
            "id": "opening-shot", "scene_id": "opening",
            "start_ms": 0, "end_ms": 2000,
            "cast": ["mara"],
            "asset_refs": [{"object_id": "storyboard", "sha256":
                            file_sha(root / "sample-keyframe.txt")}],
            "dialogue_ids": ["line-1"],
            "symbolic_beat_ids": ["plant-trust"],
            "semantic_projection_ids": ["visual-handoff"],
            "location": "A fictional threshold room",
            "camera": "Hold on Mara and the talisman exchange",
            "blocking": "Mara transfers an object to an ally",
            "initial_state": {
                "character_positions": "Mara holds the talisman",
                "prop_state": "Talisman in Mara's hand",
                "environment_state": "Interior lighting stable"},
            "exit_state": {
                "character_positions": "Mara's hand is empty",
                "prop_state": "Talisman transferred to ally",
                "environment_state": "Interior lighting unchanged"},
            "soundscape": "Room tone plus Mara speaking",
            "negative_constraints": ["Do not change speaker voice identity",
                                     "Do not move the talisman back to Mara"]
        }]
    }
    reviews = {
        "version": 1, "contract_sha256": digest(shot_contract),
        "reviews": [{
            "shot_id": "opening-shot", "evidence_sha256":
                file_sha(root / "sample-keyframe.txt"),
            "reviewer": "synthetic test reviewer",
            "evidence": "synthetic data, not real cinematic review",
            "identity_preserved": True, "environment_preserved": True,
            "dialogue_binding_preserved": True,
            "state_transition_preserved": True, "symbolism_preserved": True,
            "meaning_preserved": True, "approved": True
        }]
    }
    shot_report = audit_shot_evidence(shot_contract, package, semantic,
                                      program, graph, reviews)
    for filename, payload in (("shot-contract.json", shot_contract),
                              ("shot-reviews.json", reviews),
                              ("shot-report.json", shot_report)):
        (root / filename).write_text(json.dumps(payload, indent=2))
    return {"shot_contract": "shot-contract.json", "shot_report": "shot-report.json",
            "semantic_contract": "semantic.json",
            "semantic_report": "semantic-report.json",
            "production_graph": "production-graph.json",
            "production_graph_report": "production-report.json",
            "collaboration_package": "collaboration.json",
            "collaboration_ack": "ack.json", "performance_report": "performance.json",
            "symbolic_program": "symbolic.json",
            "symbolic_report": "symbolic-report.json"}
