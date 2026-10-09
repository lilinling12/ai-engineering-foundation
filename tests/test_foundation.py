import json
from pathlib import Path
import tempfile
import unittest
from foundation.__main__ import catalog, init_project, verify_project, main

class FoundationTests(unittest.TestCase):
    def test_catalog_four_packs_two_runnable(self):
        packs = catalog()
        self.assertEqual(set(packs), {"python-service", "typescript-api", "java-spring", "wechat-native"})
        self.assertEqual(sum(x["status"] == "runnable" for x in packs.values()), 2)

    def test_python_golden_path(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "fresh"
            init_project("python-service", out)
            self.assertTrue((out / "AGENTS.md").exists())
            self.assertTrue(verify_project(out))
            evidence = json.loads((out / ".foundation/evidence.json").read_text())
            self.assertEqual(evidence["result"], "pass")
            self.assertEqual(evidence["trustLevel"], "local-unattested")

    def test_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "existing"
            out.mkdir()
            (out / "keep").write_text("keep")
            with self.assertRaises(FileExistsError):
                init_project("python-service", out)
            self.assertEqual((out / "keep").read_text(), "keep")

    def test_contract_only_cannot_scaffold(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                init_project("java-spring", Path(temp) / "java")

    def test_manifest_must_not_define_commands(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "python"
            init_project("python-service", out)
            path = out / ".foundation/project.json"
            manifest = json.loads(path.read_text())
            manifest["command"] = "rm -rf /"
            path.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                verify_project(out)


    def test_failed_validation_emits_negative_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "broken"
            init_project("python-service", out)
            (out / "tests/test_core.py").write_text(
                chr(10).join([
                    "import unittest",
                    "class Broken(unittest.TestCase):",
                    "    def test_failure(self):",
                    "        self.assertEqual(1, 2)",
                    "",
                ]),
                encoding="utf-8"
            )
            self.assertFalse(verify_project(out))
            self.assertEqual(main(["verify", "--project", str(out)]), 1)
            evidence = json.loads((out / ".foundation/evidence.json").read_text(encoding="utf-8"))
            self.assertEqual(evidence["result"], "fail")
            self.assertEqual(evidence["checks"][0]["id"], "unit-test")
            self.assertEqual(evidence["checks"][0]["result"], "fail")
            self.assertNotEqual(evidence["checks"][0]["exitCode"], 0)
            self.assertIn("AssertionError", evidence["checks"][0]["outputTail"])
            self.assertEqual(evidence["trustLevel"], "local-unattested")

    def test_reject_symlinked_output_without_touching_target(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            original = root / "existing"
            original.mkdir()
            (original / "important").write_text("keep", encoding="utf-8")
            linked = root / "symlink"
            try:
                linked.symlink_to(original, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("Creating symlinks requires OS privileges")
            with self.assertRaises(FileExistsError):
                init_project("python-service", linked)
            self.assertEqual((original / "important").read_text(encoding="utf-8"), "keep")
            self.assertFalse((original / ".foundation").exists())

    def test_incompatible_project_manifest_denied(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "bad"
            init_project("python-service", out)
            path = out / ".foundation/project.json"
            manifest = json.loads(path.read_text(encoding="utf-8"))
            manifest["contract"] = "foundation.project/v999"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(ValueError):
                verify_project(out)

    def test_unknown_stack(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                init_project("../../untrusted", Path(temp) / "unsafe")

if __name__ == "__main__":
    unittest.main()

