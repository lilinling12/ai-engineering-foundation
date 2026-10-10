import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from foundation.codex_live import (
    MAX_INFERENCE_SECONDS, _minimized_env, run_codex_fixture,
)
from foundation.model_gateway import ModelGatewayError

SYNTHETIC_OUTPUT = json.dumps({
    "summary": "Create pure greeting function",
    "changes": [{
        "path": "app/greeting.py",
        "content": "def greet(name: str) -> str:\n    return 'Hello, ' + name\n",
    }],
})

class CodexLiveRunnerTests(unittest.TestCase):
    def setup_fixture(self, root):
        binary = root / "codex"
        binary.write_text("trusted stub; NEVER executed in unit tests")
        return binary

    def _fake_runner(self, calls, *, answer=SYNTHETIC_OUTPUT, exit_code=0, version="codex-cli 0.162.1"):
        def run(args, **kwargs):
            calls.append((args, kwargs))
            if args[-1] == "--version":
                return subprocess.CompletedProcess(args, 0, version, "")
            idx = args.index("--output-last-message")
            target = Path(args[idx + 1])
            if exit_code == 0:
                target.write_text(answer, encoding="utf-8")
            return subprocess.CompletedProcess(args, exit_code, "", "")
        return run

    def test_no_inference_without_all_manual_gates(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            binary = self.setup_fixture(root)
            with patch.dict(os.environ, {"FOUNDATION_DISPOSABLE_RUNTIME": "yes"}):
                for paid,ack in [(False,False),(True,False),(False,True)]:
                    with self.subTest(paid=paid, ack=ack), self.assertRaises(ModelGatewayError):
                        run_codex_fixture(root/"out", "test-model",
                                          paid_opt_in=paid, risk_acknowledged=ack,
                                          api_key="temporary-token", cli_binary=binary)
            with patch.dict(os.environ, {"FOUNDATION_DISPOSABLE_RUNTIME": "no"}):
                with self.assertRaises(ModelGatewayError):
                    run_codex_fixture(root/"out", "test-model", paid_opt_in=True,
                                      risk_acknowledged=True, api_key="temporary-token",
                                      cli_binary=binary)

    def test_real_process_interface_is_invoked_without_raw_logging(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            binary = self.setup_fixture(root)
            calls=[]
            with patch.dict(os.environ, {"FOUNDATION_DISPOSABLE_RUNTIME": "yes"}):
                receipt = run_codex_fixture(
                    root/"out", "test-model", paid_opt_in=True, risk_acknowledged=True,
                    api_key="SENSITIVE_EXAMPLE_KEY", cli_binary=binary,
                    runner=self._fake_runner(calls)
                )
            evidence=json.loads(receipt.read_text(encoding="utf-8"))
            proposal=json.loads((root/"out"/"proposal.json").read_text(encoding="utf-8"))
            self.assertEqual(evidence["provider"], "codex-cli")
            self.assertEqual(evidence["result"], "pending-review")
            self.assertFalse(evidence["executed"])
            self.assertFalse(evidence["applied"])
            self.assertEqual(proposal["changes"][0]["path"], "app/greeting.py")
            self.assertEqual(len(calls),2)
            cmd, kw = calls[1]
            self.assertIn("read-only", cmd)
            self.assertIn("--ephemeral", cmd)
            self.assertIn("--output-schema", cmd)
            self.assertNotIn("SENSITIVE_EXAMPLE_KEY", json.dumps(evidence))
            self.assertNotIn("SENSITIVE_EXAMPLE_KEY", json.dumps(proposal))
            self.assertNotIn("SENSITIVE_EXAMPLE_KEY", str(cmd))
            self.assertNotIn("OPENAI_SECRET_EXTRA", kw["env"])
            self.assertEqual(kw["stdout"], subprocess.DEVNULL)
            self.assertEqual(kw["stderr"], subprocess.DEVNULL)
            self.assertEqual(kw["timeout"], MAX_INFERENCE_SECONDS)

    def test_untrusted_model_paths_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            binary=self.setup_fixture(root)
            malicious=json.dumps({"summary":"bad","changes":[
                {"path":"../AGENTS.md","content":"tamper"}]})
            with patch.dict(os.environ, {"FOUNDATION_DISPOSABLE_RUNTIME":"yes"}):
                with self.assertRaises(ModelGatewayError):
                    run_codex_fixture(root/"out", "test-model", paid_opt_in=True,
                                      risk_acknowledged=True, cli_binary=binary,
                                      api_key="sample-token",
                                      runner=self._fake_runner([], answer=malicious))
            self.assertFalse((root/"out").exists())

    def test_wrong_cli_version_and_failures_are_redacted(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            binary=self.setup_fixture(root)
            with patch.dict(os.environ, {"FOUNDATION_DISPOSABLE_RUNTIME":"yes"}):
                with self.assertRaises(ModelGatewayError):
                    run_codex_fixture(root/"out", "test-model", paid_opt_in=True,
                                      risk_acknowledged=True, cli_binary=binary,
                                      api_key="SECRET", runner=self._fake_runner([],version="codex-cli 0.0.1"))
                with self.assertRaises(ModelGatewayError) as ex:
                    run_codex_fixture(root/"out", "test-model", paid_opt_in=True,
                                      risk_acknowledged=True, cli_binary=binary,
                                      api_key="SECRET", runner=self._fake_runner([],exit_code=9))
                self.assertNotIn("SECRET",str(ex.exception))
            self.assertFalse((root/"out").exists())

    def test_minimized_env_drops_ambient_secrets(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(os.environ, {
                "PATH": "/bin", "AWS_SECRET_ACCESS_KEY": "sensitive",
                "GITHUB_TOKEN": "private", "OPENAI_API_KEY":"ambient"
            }, clear=True):
                env=_minimized_env(Path(temp),"ephemeral")
                self.assertEqual(env["OPENAI_API_KEY"],"ephemeral")
                self.assertNotIn("AWS_SECRET_ACCESS_KEY",env)
                self.assertNotIn("GITHUB_TOKEN",env)

if __name__ == "__main__":
    unittest.main()
