from copy import deepcopy
import json
import unittest

from cinemaswarm_world import Character, Event, World
from scripts.compile_episode import compile_episode


class EpisodeCompilerTests(unittest.TestCase):
    def setUp(self):
        at = "2026-01-01T00:00:00Z"
        world = World("test", at)
        world.instantiate(Character("sailor", "Sailor", at))
        world.commit(Event("arrival", at, "sailor", "observation", detail="A sail appears."))
        self.project = {
            "version": 1, "title": "Arrival",
            "worldSeed": json.loads(world.to_json()),
            "script": "Genre: maritime fantasy\nWorld Type: Island harbor\nPlot Synopsis: A sail arrives.",
            "refs": [{"id": "sail", "name": "Blue sail", "url": "asset:blue"}],
            "shots": [
                {"name": "Harbor", "sourceEvent": "arrival", "direction": "Wide harbor", "refs": ["sail"]},
                {"name": "Lookout", "sourceEvent": "arrival", "direction": "Hold the face", "refs": []},
            ],
        }
        self.registry = [{"id": "camera", "mission": "Plan coverage", "output": "shot plan",
                          "approval_gate": "review"}]

    def test_project_drives_coverage_and_revision(self):
        original = compile_episode(self.project, self.registry)
        self.assertIn("first 2 connected clips", original["showrunner_request"])
        self.assertIn("A sail appears.", original["showrunner_request"])
        self.assertEqual(len(original["manifest"]["coverage"]), 2)
        changed = deepcopy(self.project)
        changed["refs"][0]["url"] = "asset:red"
        updated = compile_episode(changed, self.registry)
        self.assertNotEqual(updated["revision"], original["revision"])
        self.assertEqual(updated["manifest"]["coverage"][1], original["manifest"]["coverage"][1])
        changed["script"] += "\nNew ending."
        self.assertNotEqual(compile_episode(changed, self.registry)["manifest"]["episode_source_revision"],
                            original["manifest"]["episode_source_revision"])

    def test_missing_event_or_asset_blocks_compilation(self):
        for field, value in [("sourceEvent", "missing"), ("refs", ["missing"])]:
            changed = deepcopy(self.project)
            changed["shots"][0][field] = value
            with self.assertRaises(ValueError):
                compile_episode(changed, self.registry)
