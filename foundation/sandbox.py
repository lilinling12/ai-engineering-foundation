"""Fail-closed sandbox command planning, not an executor.

A valid Docker command specification alone does not establish a security boundary.
No command is executed by this module. Never mount production repos or secrets.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import re

_IMAGE = re.compile(r"^[a-z0-9][a-z0-9._/-]*@sha256:[0-9a-f]{64}$")
_ALLOWED = {
    "python-unit": ("python", "-B", "-m", "unittest", "discover", "-s", "tests", "-v"),
    "python-eval": ("python", "-B", "-m", "unittest", "discover", "-s", "/acceptance", "-v"),
}

class SandboxPolicyError(ValueError):
    pass

@dataclass(frozen=True)
class SandboxPolicy:
    image_digest: str
    network: str = "none"
    memory_mb: int = 256
    cpus: int = 1
    pids: int = 64
    timeout_seconds: int = 60

    def validate(self) -> None:
        if not _IMAGE.fullmatch(self.image_digest):
            raise SandboxPolicyError("Image must be pinned by sha256 digest")
        if self.network != "none":
            raise SandboxPolicyError("No network may be provisioned by this runner")
        if not (64 <= self.memory_mb <= 1024 and 1 <= self.cpus <= 2 and
                16 <= self.pids <= 128 and 1 <= self.timeout_seconds <= 120):
            raise SandboxPolicyError("Resources exceed the reviewed local policy")

def plan_docker_run(workspace: Path, check_id: str, policy: SandboxPolicy, *, acceptance_dir: Path | None = None) -> tuple[str, ...]:
    """Return fixed argv for a tightly constrained offline check; execute nothing."""
    policy.validate()
    if check_id not in _ALLOWED:
        raise SandboxPolicyError("Check not registered in trusted adapter")
    if not workspace.is_absolute() or not workspace.is_dir() or workspace.is_symlink():
        raise SandboxPolicyError("Existing absolute non-symlink workspace required")
    root = workspace.resolve(strict=True)
    if root.is_symlink():
        raise SandboxPolicyError("Unsafe workspace")
    mounts: tuple[str, ...] = ()
    if check_id == "python-eval":
        if (acceptance_dir is None or not acceptance_dir.is_absolute() or
                not acceptance_dir.is_dir() or acceptance_dir.is_symlink()):
            raise SandboxPolicyError("Trusted acceptance directory required")
        accepted = acceptance_dir.resolve(strict=True)
        if accepted == root or root in accepted.parents or accepted in root.parents:
            raise SandboxPolicyError("Acceptance must be separate from project")
        mounts = ("--mount", f"type=bind,src={accepted},dst=/acceptance,readonly")
    elif acceptance_dir is not None:
        raise SandboxPolicyError("Unexpected acceptance mount")
    # Caller must create a dedicated, non-sensitive workspace. No docker.sock,
    # home directory, credentials or host network access are mounted.
    return (
        "docker", "run", "--rm", "--pull=never",
        "--network=none", "--read-only", "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--user=65534:65534", "--pids-limit", str(policy.pids),
        "--memory", f"{policy.memory_mb}m", "--cpus", str(policy.cpus),
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=32m",
        "--env=PYTHONDONTWRITEBYTECODE=1", "--env=PYTHONPATH=/workspace", "--env=HOME=/tmp",
        "--mount", f"type=bind,src={root},dst=/workspace,readonly",
        *mounts,
        "--workdir", "/workspace", policy.image_digest, *_ALLOWED[check_id],
    )

def command_catalog() -> tuple[str, ...]:
    return tuple(sorted(_ALLOWED))
