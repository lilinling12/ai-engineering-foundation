import json
from pathlib import Path
import tempfile
import unittest

from foundation.codex_cli_adapter import (
    CODEX_VERSION, PINNED_TOOL, build_codex_request, validate_codex_final_text,
)
from foundation.harness import AuthoritySnapshot, DEMO_TASK, load_task
from foundation.model_gateway import ModelGatewayError


class CodexCliAdapterTests(unittest.TestCase):
    def setup_request(self, base: Path):
        work = base / "work"
        control = base / "control"
        work.mkdir()
        control.mkdir()
        task = load_task(DEMO_TASK)
        authority = AuthoritySnapshot("a" * 64, "# AGENTS", "# CURRENT")
        return task, authority, work, control / "schema.json", control / "result.json"

    def test_strict_request_no_execution_or_unsafe_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            task, auth, work, schema, result = self.setup_request(Path(tmp))
            plan = build_codex_request(task, auth, model="gpt-6", worktree=work,
                                       schema_path=schema, result_path=result)
            self.assertEqual(plan.execution_status, "NOT_EXECUTED")
            self.assertEqual(plan.tool_version, CODEX_VERSION)
            self.assertTrue(PINNED_TOOL.endswith(CODEX_VERSION))
            self.assertEqual(plan.argv[:2], ("codex", "exec"))
            for needed in ("--sandbox", "read-only", "--ephemeral",
                           "--ignore-user-config", "--output-schema",
                           "--output-last-message", "--cd"):
                self.assertIn(needed, plan.argv)
            for forbidden in ("danger-full-access", "--yolo", "--full-auto",
                              "--dangerously-bypass-approvals-and-sandbox",
                              "--add-dir", "--search", "workspace-write"):
                self.assertNotIn(forbidden, plan.argv)
            self.assertEqual(plan.argv[-1], "-")
            self.assertEqual(json.loads(plan.stdin)["allowedPaths"], ["app/greeting.py"])
            self.assertFalse(result.exists())
            self.assertFalse(schema.exists())
            self.assertEqual(json.loads(plan.schema_json)["additionalProperties"], False)

    def test_reject_unreviewed_command_or_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            task, auth, work, schema, result = self.setup_request(Path(tmp))
            for kwargs in (
                {"codex_executable": "bash"},
                {"model": "--yolo"},
                {"worktree": Path(".")},
                {"schema_path": Path("schema.json")},
                {"result_path": work / "result.json"},
                {"result_path": schema},
            ):
                with self.subTest(kwargs=kwargs), self.assertRaises(ModelGatewayError):
                    build_codex_request(task, auth, model="gpt-6",
                                        worktree=work, schema_path=schema,
                                        result_path=result, **kwargs)

    def test_valid_proposal_parsed_without_execution(self):
        task = load_task(DEMO_TASK)
        raw = json.dumps({"summary": "Implement greeting",
                          "changes": [{"path": "app/greeting.py",
                                       "content": "def greet(name: str) -> str:\n    return 'Hello, ' + name\n"}]})
        result = validate_codex_final_text(raw, task)
        self.assertEqual(result.changes[0].path, "app/greeting.py")

    def test_invalid_proposals_denied(self):
        task = load_task(DEMO_TASK)
        for raw in (
            "not-json",
            json.dumps({"summary": "bad", "changes":
                        [{"path": "../AGENTS.md", "content": "tamper"}]}),
            json.dumps({"summary": "bad", "changes":
                        [{"path": "app/greeting.py", "content": "x"}], "execute": True}),
        ):
            with self.subTest(raw=raw), self.assertRaises(ModelGatewayError):
                validate_codex_final_text(raw, task)

if __name__ == "__main__":
    unittest.main()
