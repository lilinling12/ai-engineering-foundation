"""Codex binary supply-chain gate: exact package and integrity-pinned lock."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "tools" / "codex-cli"

class CodexSupplyChainTests(unittest.TestCase):
    def test_codex_lockfile_pinned_and_complete(self):
        package = json.loads((TOOL / "package.json").read_text(encoding="utf-8"))
        lock = json.loads((TOOL / "package-lock.json").read_text(encoding="utf-8"))
        self.assertEqual(lock["lockfileVersion"], 3)
        self.assertEqual(lock["packages"][""]["devDependencies"], package["devDependencies"])
        self.assertEqual(package["devDependencies"]["@openai/codex"], "0.162.1")
        self.assertEqual(lock["packages"]["node_modules/@openai/codex"]["version"], "0.162.1")
        self.assertEqual(len(lock["packages"]), 8)
        for name, data in lock["packages"].items():
            if name:
                with self.subTest(name=name):
                    self.assertRegex(data["integrity"], r"^sha512-[A-Za-z0-9+/]+={0,2}$")
                    self.assertTrue(data["resolved"].startswith("https://registry.npmjs.org/"))

if __name__ == "__main__":
    unittest.main()
