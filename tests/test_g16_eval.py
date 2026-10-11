import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from foundation.g16_eval import (
    _docker_evaluate, _write_synthetic_module, ALLOWED_WORKSPACES,
    OfflineCheck, smoke,
)
from foundation.docker_executor import ExecutionDenied
from foundation.sandbox import SandboxPolicyError

HOSTED = {"GITHUB_ACTIONS": "true", "RUNNER_ENVIRONMENT": "github-hosted",
          "FOUNDATION_EPHEMERAL_RUNNER": "yes"}

DIGEST = "python@sha256:" + "a"*64


class SyntheticEvalContractTests(unittest.TestCase):
    def test_smoke_report_emits_structured_statuses(self):
        import json
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            expected = [
                OfflineCheck("pass", 0, True),
                OfflineCheck("fail", 1, True),
                OfflineCheck("timeout", None, True),
            ]
            with patch.dict(os.environ, {"RUNNER_TEMP": str(root)}, clear=False), \
                 patch("foundation.g16_eval.ROOT", root), \
                 patch("foundation.g16_eval.require_disposable_host"), \
                 patch("foundation.g16_eval._docker_evaluate", side_effect=expected):
                self.assertEqual(smoke(DIGEST), 0)
            artifact = json.loads((root/"artifacts/g16-synthetic-offline-eval.json").read_text())
            self.assertEqual(artifact["result"], "pass")
            self.assertFalse(artifact["modelInvoked"])
            self.assertEqual(artifact["checks"]["staged-good"]["status"], "pass")
            self.assertEqual(artifact["checks"]["negative-wrong-answer"]["status"], "fail")
            self.assertEqual(artifact["checks"]["negative-timeout"]["status"], "timeout")

    def test_smoke_rejects_failed_expected_checks(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            outcomes = [
                OfflineCheck("fail", 1, True),
                OfflineCheck("fail", 1, True),
                OfflineCheck("timeout", None, True),
            ]
            with patch.dict(os.environ, {"RUNNER_TEMP": str(root)}, clear=False), \
                 patch("foundation.g16_eval.ROOT", root), \
                 patch("foundation.g16_eval.require_disposable_host"), \
                 patch("foundation.g16_eval._docker_evaluate", side_effect=outcomes):
                self.assertEqual(smoke(DIGEST), 1)

    def test_refuse_outside_host_and_unreviewed_paths(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            stage = root / "staged"
            stage.mkdir()
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaises(ExecutionDenied):
                    _docker_evaluate(stage, root, DIGEST)
            with patch.dict(os.environ, HOSTED, clear=True), \
                 patch("foundation.docker_executor.shutil.which", return_value="/usr/bin/docker"), \
                 patch("foundation.g16_eval.subprocess.Popen") as run:
                with self.assertRaises(SandboxPolicyError):
                    _docker_evaluate(root, root, DIGEST)
                outsider = root / "unreviewed"
                outsider.mkdir()
                with self.assertRaises(SandboxPolicyError):
                    _docker_evaluate(outsider, root, DIGEST)
                run.assert_not_called()

    def test_negative_fixture_files_not_generic(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            with self.assertRaises(SandboxPolicyError):
                _write_synthetic_module(root,"arbitrary", "print('unsafe')")
            self.assertFalse((root/"arbitrary").exists())

    def test_nonroot_readonly_offline_and_cleanup_command(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            stage = root / "staged"
            stage.mkdir()
            proc = MagicMock()
            proc.wait.return_value = 0
            delete = subprocess.CompletedProcess(["docker","rm"],0)
            with patch.dict(os.environ, HOSTED, clear=True), \
                 patch("foundation.docker_executor.shutil.which", return_value="/usr/bin/docker"), \
                 patch("foundation.g16_eval.subprocess.Popen", return_value=proc) as launched, \
                 patch("foundation.g16_eval.subprocess.run", return_value=delete) as cleanup:
                outcome = _docker_evaluate(stage,root,DIGEST)
            self.assertEqual(outcome, OfflineCheck("pass",0,True))
            args = launched.call_args.args[0]
            self.assertIn("--network=none", args)
            self.assertIn("--read-only", args)
            self.assertIn("--cap-drop=ALL", args)
            self.assertIn("--user=65534:65534", args)
            self.assertIn("--pids-limit", args)
            self.assertIn("--pull=never", args)
            self.assertIn("--mount", args)
            self.assertFalse(any("docker.sock" in arg for arg in args))
            self.assertEqual(cleanup.call_args.args[0][:3],["docker","rm","-f"])
            self.assertEqual(launched.call_args.kwargs["stdout"],subprocess.DEVNULL)
            self.assertEqual(launched.call_args.kwargs["stderr"],subprocess.DEVNULL)

    def test_timeout_forcibly_removes_daemon_container(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            stage=root/"staged"
            stage.mkdir()
            proc=MagicMock()
            proc.wait.side_effect=[subprocess.TimeoutExpired("docker",3),None]
            remove=subprocess.CompletedProcess(["docker","rm"],0)
            with patch.dict(os.environ,HOSTED,clear=True), \
                 patch("foundation.docker_executor.shutil.which",return_value="/usr/bin/docker"), \
                 patch("foundation.g16_eval.subprocess.Popen",return_value=proc), \
                 patch("foundation.g16_eval.subprocess.run",return_value=remove):
                result=_docker_evaluate(stage,root,DIGEST,seconds=3)
            self.assertEqual(result.status,"timeout")
            self.assertTrue(result.cleanup_confirmed)
            proc.kill.assert_called_once()

    def test_uncertain_daemon_cleanup_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            stage=root/"staged"
            stage.mkdir()
            proc=MagicMock()
            proc.wait.return_value=0
            remove=subprocess.CompletedProcess(["docker","rm"],1)
            inspect=subprocess.CompletedProcess(["docker","container","inspect"],1,b"",b"Cannot connect to Docker daemon")
            with patch.dict(os.environ,HOSTED,clear=True), \
                 patch("foundation.docker_executor.shutil.which",return_value="/usr/bin/docker"), \
                 patch("foundation.g16_eval.subprocess.Popen",return_value=proc), \
                 patch("foundation.g16_eval.subprocess.run",side_effect=[remove,inspect]):
                result=_docker_evaluate(stage,root,DIGEST)
            self.assertEqual(result.status,"runner-error")
            self.assertFalse(result.cleanup_confirmed)

if __name__ == "__main__":
    unittest.main()
