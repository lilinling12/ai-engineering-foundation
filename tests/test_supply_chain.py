"""Repository and generated TS template supply-chain guardrails (stdlib only)."""
from pathlib import Path
import json
import re
import unittest

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "templates" / "typescript-api" / "package.json"
LOCK = ROOT / "templates" / "typescript-api" / "package-lock.json"
WORKFLOW = ROOT / ".github" / "workflows" / "foundation-ci.yml"

class SupplyChainTests(unittest.TestCase):
    def test_npm_lock_matches_manifest(self):
        package = json.loads(PACKAGE.read_text(encoding="utf-8"))
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        self.assertEqual(lock["lockfileVersion"], 3)
        self.assertEqual(lock["name"], package["name"])
        self.assertEqual(lock["version"], package["version"])
        self.assertEqual(lock["packages"][""]["devDependencies"], package["devDependencies"])
        installed = {p.removeprefix("node_modules/"): v for p,v in lock["packages"].items() if p}
        self.assertEqual(set(installed), {"typescript", "@types/node", "undici-types"})
        for name, meta in installed.items():
            with self.subTest(name=name):
                self.assertRegex(meta["integrity"], r"^sha512-[A-Za-z0-9+/]+={0,2}$")
                self.assertTrue(meta["resolved"].startswith("https://registry.npmjs.org/"))
                self.assertRegex(meta["version"], r"^\d+\.\d+\.\d+$")
        for name, version in package["devDependencies"].items():
            self.assertEqual(installed[name]["version"], version)

    def test_actions_are_sha_pinned_and_install_is_frozen(self):
        content = WORKFLOW.read_text(encoding="utf-8")
        refs = re.findall(r"^\s*- uses: ([^\s]+)$", content, flags=re.MULTILINE)
        self.assertGreaterEqual(len(refs), 3)
        for ref in refs:
            with self.subTest(ref=ref):
                self.assertRegex(ref, r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@[0-9a-f]{40}$")
        self.assertIn("npm ci --ignore-scripts --no-audit --no-fund", content)
        self.assertNotIn("npm install", content)
        self.assertIn("persist-credentials: false", content)
        self.assertIn("contents: read", content)

if __name__ == "__main__":
    unittest.main()
