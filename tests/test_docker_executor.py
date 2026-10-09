import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import subprocess
import unittest

from foundation.docker_executor import ExecutionDenied, run_fixture_check, require_disposable_host
from foundation.sandbox import SandboxPolicy, SandboxPolicyError, plan_docker_run

PIN = "python@sha256:" + "a" * 64
HOSTED = {"GITHUB_ACTIONS": "true", "RUNNER_ENVIRONMENT": "github-hosted",
          "FOUNDATION_EPHEMERAL_RUNNER": "yes"}

class ExecutorContractTests(unittest.TestCase):
    def test_no_local_execution_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ExecutionDenied):
                require_disposable_host()

    def test_reject_self_hosted_runner(self):
        with patch.dict(os.environ, {**HOSTED, "RUNNER_ENVIRONMENT": "self-hosted"}, clear=True):
            with self.assertRaises(ExecutionDenied):
                require_disposable_host()

    def test_acceptance_is_separate_readonly_mount(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "work").mkdir()
            (root / "accept").mkdir()
            cmd = plan_docker_run(root / "work", "python-eval", SandboxPolicy(PIN),
                                  acceptance_dir=root / "accept")
            self.assertTrue(any("dst=/acceptance,readonly" in x for x in cmd))
            self.assertIn("--env=PYTHONPATH=/workspace", cmd)
            with self.assertRaises(SandboxPolicyError):
                plan_docker_run(root / "work", "python-eval", SandboxPolicy(PIN))
            with self.assertRaises(SandboxPolicyError):
                plan_docker_run(root / "work", "python-eval", SandboxPolicy(PIN),
                                acceptance_dir=root / "work")

    def test_success_and_always_cleanup(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            proc = MagicMock()
            proc.returncode = 0
            proc.communicate.return_value = ("ok", "")
            with patch.dict(os.environ, HOSTED, clear=True), \
                 patch("foundation.docker_executor.shutil.which", return_value="/usr/bin/docker"), \
                 patch("foundation.docker_executor.subprocess.Popen", return_value=proc) as spawn, \
                 patch("foundation.docker_executor.subprocess.run") as cleanup:
                res = run_fixture_check(workspace, "python-unit", SandboxPolicy(PIN))
            self.assertEqual(res.status, "pass")
            argv = spawn.call_args.args[0]
            self.assertEqual(argv[:4:3], ["docker", "foundation-g12-" + argv[3].split("foundation-g12-")[-1]])
            self.assertEqual(argv[1:3], ["run", "--name"])
            self.assertEqual(cleanup.call_args.args[0][:3], ["docker", "rm", "-f"])

    def test_timeout_kills_client_and_container(self):
        with tempfile.TemporaryDirectory() as temp:
            proc = MagicMock()
            proc.communicate.side_effect = [subprocess.TimeoutExpired("docker", 3), ("", "")]
            with patch.dict(os.environ, HOSTED, clear=True), \
                 patch("foundation.docker_executor.shutil.which", return_value="/usr/bin/docker"), \
                 patch("foundation.docker_executor.subprocess.Popen", return_value=proc), \
                 patch("foundation.docker_executor.subprocess.run") as cleanup:
                res = run_fixture_check(Path(temp), "python-unit",
                                        SandboxPolicy(PIN, timeout_seconds=3))
            self.assertEqual(res.status, "timeout")
            proc.kill.assert_called_once()
            cleanup.assert_called_once()

    def test_bad_check_rejected_before_spawning(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(os.environ, HOSTED, clear=True), \
                 patch("foundation.docker_executor.shutil.which", return_value="/usr/bin/docker"), \
                 patch("foundation.docker_executor.subprocess.Popen") as spawn:
                with self.assertRaises(SandboxPolicyError):
                    run_fixture_check(Path(temp), "arbitrary-shell", SandboxPolicy(PIN))
                spawn.assert_not_called()
