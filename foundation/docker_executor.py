"""Explicit, CI-only Docker execution of *trusted fixtures*.

This performs real docker run/cleanup on disposable GitHub-hosted runners.
It is NOT a hardened multi-tenant sandbox and it MUST NOT be given arbitrary
agent output, external repositories, production volumes or credentials.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import shutil
import subprocess
import uuid

from .sandbox import SandboxPolicy, SandboxPolicyError, plan_docker_run

# The G1.2 Docker capability is limited to reviewed in-repository fixtures.
# Environment variable checks are NOT authentication of the host.
FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "offline-sandbox"
TRUSTED_FIXTURE_NAMES = {
    "python-eval": frozenset({"project-good", "project-bad"}),
    "python-unit": frozenset({"policy", "hang"}),
}

def _verify_fixture_identity(workspace: Path, check_id: str, acceptance_dir: Path | None) -> None:
    if check_id not in TRUSTED_FIXTURE_NAMES:
        raise ExecutionDenied("No reviewed fixture for this check")
    if workspace.is_symlink() or not workspace.is_dir() or not workspace.is_absolute():
        raise ExecutionDenied("Workspace must be a reviewed repository fixture")
    reviewed = { (FIXTURES / name).resolve() for name in TRUSTED_FIXTURE_NAMES[check_id] }
    if workspace.resolve() not in reviewed:
        raise ExecutionDenied("Arbitrary workspace execution is prohibited in G1.2")
    if check_id == "python-eval":
        if (acceptance_dir is None or acceptance_dir.is_symlink()
                or acceptance_dir.resolve() != (FIXTURES / "acceptance").resolve()):
            raise ExecutionDenied("Acceptance oracle must be repository-owned and separate")
    elif acceptance_dir is not None:
        raise ExecutionDenied("Unexpected acceptance oracle")

class ExecutionDenied(PermissionError):
    pass

@dataclass(frozen=True)
class CheckResult:
    check_id: str
    status: str
    exit_code: int | None
    output_tail: str
    timeout_seconds: int

def require_disposable_host() -> None:
    if not (
        os.environ.get("GITHUB_ACTIONS") == "true"
        and os.environ.get("RUNNER_ENVIRONMENT") == "github-hosted"
        and os.environ.get("FOUNDATION_EPHEMERAL_RUNNER") == "yes"
    ):
        raise ExecutionDenied("Requires explicitly opted-in GitHub-hosted ephemeral CI")
    if shutil.which("docker") is None:
        raise ExecutionDenied("Docker CLI not available")

def run_fixture_check(
    workspace: Path, check_id: str, policy: SandboxPolicy,
    *, acceptance_dir: Path | None = None,
) -> CheckResult:
    """Run a *repository-owned* fixture, never user-selected commands or repos.

    A unique container name permits forced daemon-side cleanup on timeout.
    The Docker daemon itself is an elevated trust boundary.
    """
    require_disposable_host()
    _verify_fixture_identity(workspace, check_id, acceptance_dir)
    command = list(plan_docker_run(workspace, check_id, policy, acceptance_dir=acceptance_dir))
    name = "foundation-g12-" + uuid.uuid4().hex[:20]
    command[2:2] = ["--name", name]
    output = ""
    exit_code: int | None = None
    status = "runner-error"
    proc: subprocess.Popen[str] | None = None
    try:
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            stdout, stderr = proc.communicate(timeout=policy.timeout_seconds)
            exit_code = proc.returncode
            output = (stdout or "") + "\n" + (stderr or "")
            status = "pass" if exit_code == 0 else "fail"
        except subprocess.TimeoutExpired:
            status = "timeout"
            output = f"Exceeded {policy.timeout_seconds}s; forced Docker container removal"
            proc.kill()
            proc.communicate(timeout=10)
    except (OSError, subprocess.SubprocessError) as exc:
        status = "runner-error"
        output = type(exc).__name__ + ": " + str(exc)[:300]
    finally:
        # Killing docker CLI alone does NOT guarantee container termination.
        # Always attempt daemon-side removal, including successful --rm cases.
        try:
            cleanup = subprocess.run(
                ["docker", "rm", "-f", name], timeout=15,
                capture_output=True, text=True, check=False
            )
            if cleanup.returncode != 0:
                # A normally completed --rm container already disappeared;
                # that is distinguishable from a still-running container or
                # an unavailable Docker daemon only with a follow-up inspect.
                inspect = subprocess.run(
                    ["docker", "container", "inspect", name], timeout=15,
                    capture_output=True, text=True, check=False
                )
                missing = ("No such object" in inspect.stderr or
                           "No such container" in inspect.stderr)
                if inspect.returncode == 0 or not missing:
                    status = "runner-error"
                    output += "\nContainer removal failed or absence not verified"
        except (OSError, subprocess.SubprocessError):
            # Cleanup failure requires a failed result: never assert isolation.
            status = "runner-error"
            output += "\nDocker cleanup could not be confirmed"
    return CheckResult(check_id, status, exit_code, output[-2000:], policy.timeout_seconds)
