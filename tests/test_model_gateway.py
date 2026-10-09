import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from foundation.model_gateway import (
    ModelGatewayError, OpenAIProposalProvider, extract_proposal,
    propose_fixture, request_payload, run_live_proposal,
)
from foundation.harness import load_task, AuthoritySnapshot, DEMO_TASK

def wrapped(obj, status="completed"):
    return {"status": status, "output": [
        {"type": "reasoning", "summary": []},
        {"type": "message", "role": "assistant",
         "content": [{"type": "output_text", "text": json.dumps(obj)}]}
    ]}

GOOD = {"summary": "Implement greeting function", "changes": [
    {"path": "app/greeting.py",
     "content": "def greet(name: str) -> str:\n    return 'Hello, ' + name\n"}
]}

class GatewayTests(unittest.TestCase):
    def test_schema_and_no_tools(self):
        t = load_task(DEMO_TASK)
        a = AuthoritySnapshot("a"*64, "# AGENTS", "# CURRENT")
        p = request_payload(t, a, "test-model-1")
        self.assertFalse(p["store"])
        self.assertNotIn("tools", p)
        self.assertEqual(p["text"]["format"]["type"], "json_schema")
        self.assertEqual(p["text"]["format"]["strict"], True)
        self.assertNotIn("OPENAI_API_KEY", json.dumps(p))

    def test_proposal_success_quarantine_only(self):
        seen = []
        def fake_transport(payload, token):
            seen.append((payload["model"], token))
            return wrapped(GOOD)
        provider = OpenAIProposalProvider("test-model", "placeholder-not-real", fake_transport)
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "proposal-out"
            evpath = propose_fixture(None, provider, dest)
            ev = json.loads(evpath.read_text())
            self.assertEqual(ev["result"], "pending-review")
            self.assertFalse(ev["applied"])
            self.assertFalse(ev["executed"])
            self.assertEqual([p.name for p in dest.iterdir()], ["proposal.json", "evidence.json"])
            self.assertFalse((dest / "app").exists())
            self.assertEqual(seen[0][0], "test-model")
            with self.assertRaises(FileExistsError):
                propose_fixture(None, provider, dest)

    def test_reject_unauthorized_paths(self):
        for path in ("../evil.py", "AGENTS.md", "/tmp/out", "app/greeting.py/../x"):
            with self.subTest(path=path), self.assertRaises(ModelGatewayError):
                extract_proposal(wrapped({"summary": "bad",
                    "changes": [{"path": path, "content": "pass"}]}),
                    ("app/greeting.py",))

    def test_reject_extra_fields_duplicate_and_empty(self):
        cases = [
            {"summary": "x", "changes": [GOOD["changes"][0], GOOD["changes"][0]]},
            {"summary": "x", "changes": []},
            {"summary": "x", "changes": [{"path": "app/greeting.py", "content": ""}]},
            {"summary": "x", "changes": GOOD["changes"], "execute": True},
        ]
        for obj in cases:
            with self.subTest(obj=obj), self.assertRaises(ModelGatewayError):
                extract_proposal(wrapped(obj), ("app/greeting.py",))

    def test_reject_tool_calls_refusals_and_truncation(self):
        samples = [
            {"status": "incomplete", "output": wrapped(GOOD)["output"]},
            {"status": "completed", "output": [{"type": "function_call", "name": "shell"}]},
            {"status": "completed", "output": [{"type": "message", "role": "assistant",
                "content": [{"type": "refusal", "refusal": "No"}]}]},
            {"status": "completed", "output": [{"type": "message", "role": "assistant",
                "content": [{"type": "output_text", "text": "not json"}]}]},
        ]
        for sample in samples:
            with self.subTest(sample=sample), self.assertRaises(ModelGatewayError):
                extract_proposal(sample, ("app/greeting.py",))

    def test_missing_network_optin_or_secret_does_not_call_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"OPENAI_API_KEY": "dummy"}, clear=True), \
                    self.assertRaises(ModelGatewayError):
                run_live_proposal(Path(tmp) / "unused", "test-model", None, False)
            with patch.dict(os.environ, {}, clear=True), self.assertRaises(ModelGatewayError):
                run_live_proposal(Path(tmp) / "unused", "test-model", None, True)

    def test_bad_model_and_missing_token(self):
        for name in ("", "--full-auto", "a b", "x/../../y"):
            with self.subTest(name=name), self.assertRaises(ModelGatewayError):
                OpenAIProposalProvider(name, "dummy", lambda *_: wrapped(GOOD))
        with self.assertRaises(ModelGatewayError):
            OpenAIProposalProvider("test-model", "")

if __name__ == "__main__":
    unittest.main()
