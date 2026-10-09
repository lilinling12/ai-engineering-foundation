import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import subprocess
import unittest

from foundation.docker_executor import ExecutionDenied, run_fixture_check, require_disposable_host, FIXTURES
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
        workspace = FIXTURES / "policy"
        if True:
            proc = MagicMock()
            proc.returncode = 0
            proc.communicate.return_value = ("ok", "")
            with patch.dict(os.environ, HOSTED, clear=True), \
                 patch("foundation.docker_executor.shutil.which", return_value="/usr/bin/docker"), \
                 patch("foundation.docker_executor.subprocess.Popen", return_value=proc) as spawn, \
                 patch("foundation.docker_executor.subprocess.run") as cleanup:
                cleanup.return_value.returncode = 0
                res = run_fixture_check(workspace, "python-unit", SandboxPolicy(PIN))
            self.assertEqual(res.status, "pass")
            argv = spawn.call_args.args[0]
            self.assertEqual(argv[:4:3], ["docker", "foundation-g12-" + argv[3].split("foundation-g12-")[-1]])
            self.assertEqual(argv[1:3], ["run", "--name"])
            self.assertEqual(cleanup.call_args.args[0][:3], ["docker", "rm", "-f"])

    def test_timeout_kills_client_and_container(self):
        if True:
            proc = MagicMock()
            proc.communicate.side_effect = [subprocess.TimeoutExpired("docker", 3), ("", "")]
            with patch.dict(os.environ, HOSTED, clear=True), \
                 patch("foundation.docker_executor.shutil.which", return_value="/usr/bin/docker"), \
                 patch("foundation.docker_executor.subprocess.Popen", return_value=proc), \
                 patch("foundation.docker_executor.subprocess.run") as cleanup:
                cleanup.return_value.returncode = 0
                res = run_fixture_check(FIXTURES / "hang", "python-unit",
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
                    run_fixture_check(FIXTURES / "policy", "arbitrary-shell", SandboxPolicy(PIN))
                spawn.assert_not_called()

    def test_unreviewed_directory_never_reaches_docker(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(os.environ, HOSTED, clear=True), \
                 patch("foundation.docker_executor.shutil.which", return_value="/usr/bin/docker"), \
                 patch("foundation.docker_executor.subprocess.Popen") as spawn:
                with self.assertRaises(ExecutionDenied):
                    run_fixture_check(Path(temp), "python-unit", SandboxPolicy(PIN))
                spawn.assert_not_called()

    def test_unreviewed_acceptance_denied(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(os.environ, HOSTED, clear=True), \
                 patch("foundation.docker_executor.shutil.which", return_value="/usr/bin/docker"), \
                 patch("foundation.docker_executor.subprocess.Popen") as spawn:
                with self.assertRaises(ExecutionDenied):
                    run_fixture_check(FIXTURES / "project-good", "python-eval",
                                      SandboxPolicy(PIN), acceptance_dir=Path(temp))
                spawn.assert_not_called()

    def test_cleanup_failure_cannot_report_success(self):
        proc = MagicMock()
        proc.returncode = 0
        proc.communicate.return_value = ("ok", "")
        rm = subprocess.CompletedProcess(["docker", "rm"], 1, "", "permission denied")
        inspect = subprocess.CompletedProcess(["docker", "inspect"], 0, "container still exists", "")
        with patch.dict(os.environ, HOSTED, clear=True), \
             patch("foundation.docker_executor.shutil.which", return_value="/usr/bin/docker"), \
             patch("foundation.docker_executor.subprocess.Popen", return_value=proc), \
             patch("foundation.docker_executor.subprocess.run", side_effect=[rm, inspect]) as cleanup:
            result = run_fixture_check(FIXTURES / "policy", "python-unit", SandboxPolicy(PIN))
        self.assertEqual(result.status, "runner-error")
        self.assertEqual(cleanup.call_count, 2)

    def test_auto_removed_container_is_not_false_failure(self):
        proc = MagicMock()
        proc.returncode = 0
        proc.communicate.return_value = ("ok", "")
        rm = subprocess.CompletedProcess(["docker", "rm"], 1, "", "No such container")
        inspect = subprocess.CompletedProcess(["docker", "inspect"], 1, "", "Error: No such object: removed")
        with patch.dict(os.environ, HOSTED, clear=True), \
             patch("foundation.docker_executor.shutil.which", return_value="/usr/bin/docker"), \
             patch("foundation.docker_executor.subprocess.Popen", return_value=proc), \
             patch("foundation.docker_executor.subprocess.run", side_effect=[rm, inspect]):
            result = run_fixture_check(FIXTURES / "policy", "python-unit", SandboxPolicy(PIN))
        self.assertEqual(result.status, "pass")

    def test_daemon_unavailable_cannot_claim_cleanup_success(self):
        proc = MagicMock()
        proc.returncode = 0
        proc.communicate.return_value = ("ok", "")
        rm = subprocess.CompletedProcess(["docker", "rm"], 1, "", "cannot connect")
        inspect = subprocess.CompletedProcess(["docker", "inspect"], 1, "", "Cannot connect to the Docker daemon")
        with patch.dict(os.environ, HOSTED, clear=True), \
             patch("foundation.docker_executor.shutil.which", return_value="/usr/bin/docker"), \
             patch("foundation.docker_executor.subprocess.Popen", return_value=proc), \
             patch("foundation.docker_executor.subprocess.run", side_effect=[rm, inspect]):
            result = run_fixture_check(FIXTURES / "policy", "python-unit", SandboxPolicy(PIN))
        self.assertEqual(result.status, "runner-error")
