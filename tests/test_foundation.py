import json
from pathlib import Path
import tempfile
import unittest
from foundation.__main__ import catalog, init_project, verify_project

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

    def test_unknown_stack(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                init_project("../../untrusted", Path(temp) / "unsafe")

if __name__ == "__main__":
    unittest.main()

