"""G1.6 disposable CI proof of isolated execution for *synthetic* proposals.

This is intentionally SEPARATE from the G1.2 trusted fixture executor and
from the G1.5 inference process. No API keys, live model, customer repositories
or network access enter the container. Docker is NOT a hostile-tenant VM.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid

from .__main__ import init_project
from .docker_executor import require_disposable_host
from .harness import DEMO_TASK, FixtureProvider, load_task, restore_authority
from .model_gateway import _write_quarantine
from .codex_live import CodexMetadata
from .review_gate import read_quarantine, record_decision, stage_reviewed_proposal
from .sandbox import SandboxPolicy, SandboxPolicyError, plan_docker_run
from .g17_boundary import WRONG, HANG, require_synthetic_candidate, require_reviewed_oracle, isolated_docker_env

ROOT = Path(__file__).resolve().parent.parent
ACCEPTANCE = ROOT / "tests" / "fixtures" / "offline-sandbox" / "acceptance"
ALLOWED_WORKSPACES = frozenset({"staged", "bad-candidate", "hang-candidate"})
GOOD_TASK = "python-greeting-v0"

@dataclass(frozen=True)
class OfflineCheck:
    status: str
    exit_code: int | None
    cleanup_confirmed: bool


def _docker_evaluate(
    workspace: Path, sandbox_root: Path, image_digest: str,
    *, seconds: int = 40,
) -> OfflineCheck:
    """Private, synthetic-only Docker command execution; never generic code API."""
    require_disposable_host()
    if (not sandbox_root.is_absolute() or sandbox_root.is_symlink() or
            not sandbox_root.is_dir() or not workspace.is_absolute() or
            workspace.is_symlink() or not workspace.is_dir() or
            workspace.parent != sandbox_root or workspace.name not in ALLOWED_WORKSPACES or
            workspace.resolve(strict=True).parent != sandbox_root.resolve(strict=True)):
        raise SandboxPolicyError("Only an immediate synthetic CI workspace is allowed")
    require_synthetic_candidate(workspace)
    require_reviewed_oracle()
    client_env = isolated_docker_env(sandbox_root)
    policy = SandboxPolicy(image_digest=image_digest, timeout_seconds=seconds)
    cmd = list(plan_docker_run(workspace, "python-eval", policy, acceptance_dir=ACCEPTANCE))
    # -S disables implicit site/sitecustomize processing for this synthetic test.
    cmd.insert(cmd.index("-B") + 1, "-S")
    name = "foundation-g16-" + uuid.uuid4().hex[:20]
    cmd[2:2] = ["--name", name]
    exit_code = None
    status = "runner-error"
    cleanup_confirmed = False
    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            env=client_env,
        )
        try:
            exit_code = proc.wait(timeout=seconds)
            status = "pass" if exit_code == 0 else "fail"
        except subprocess.TimeoutExpired:
            status = "timeout"
            proc.kill()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                status = "runner-error"
    except (OSError, subprocess.SubprocessError):
        status = "runner-error"
    finally:
        # Killing docker CLI is insufficient. Check daemon-side destruction.
        try:
            delete = subprocess.run(
                ["docker", "rm", "-f", name], stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, timeout=15, check=False,
                    env=client_env,
                env=client_env,
            )
            if delete.returncode == 0:
                cleanup_confirmed = True
            else:
                inspected = subprocess.run(
                    ["docker", "container", "inspect", name],
                    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                    timeout=15, check=False,
                )
                details = inspected.stderr.decode("utf-8", errors="replace")
                cleanup_confirmed = (
                    inspected.returncode != 0 and
                    ("No such object" in details or "No such container" in details)
                )
        except (OSError, subprocess.SubprocessError):
            cleanup_confirmed = False
    if not cleanup_confirmed:
        return OfflineCheck("runner-error", exit_code, False)
    return OfflineCheck(status, exit_code, True)


def _write_synthetic_module(base: Path, name: str, content: str) -> Path:
    if name not in {"bad-candidate", "hang-candidate"}:
        raise SandboxPolicyError("Only built-in negative candidates allowed")
    dest = base / name
    dest.mkdir(mode=0o755)
    app = dest / "app"
    app.mkdir(mode=0o755)
    (app / "__init__.py").write_text("", encoding="utf-8")
    (app / "greeting.py").write_text(content, encoding="utf-8")
    return dest


def smoke(image_digest: str) -> int:
    require_disposable_host()
    # No user-supplied source, task, repo, command, acceptance, credentials or paths.
    task = load_task(DEMO_TASK)
    if task.task_id != GOOD_TASK or task.allowed_paths != ("app/greeting.py",):
        raise SandboxPolicyError("Only the reviewed synthetic task may run")
    with tempfile.TemporaryDirectory(prefix="foundation-g16-",
                                     dir=os.environ.get("RUNNER_TEMP")) as td:
        base = Path(td).resolve(strict=True)
        reference = base / "reference"
        init_project("python-service", reference)
        authority = restore_authority(reference)
        fake_model_output = FixtureProvider("fixture-pass").propose(task, authority)
        quarantine = base / "synthetic-quarantine"
        _write_quarantine(quarantine, task, authority,
                          CodexMetadata("codex-cli", "synthetic-NO-MODEL"), fake_model_output)
        _, digest = read_quarantine(quarantine)
        # A synthetic test decision, NOT actual operator identity or approval.
        decision = record_decision(quarantine, digest, "approve", base / "fixture-decision.json")
        staged = base / "staged"
        stage_evidence = stage_reviewed_proposal(quarantine, decision, staged)
        if not json.loads(stage_evidence.read_text(encoding="utf-8")).get("executed") is False:
            raise SandboxPolicyError("Staged evidence must report no execution")
        good = _docker_evaluate(staged, base, image_digest)
        bad_source = WRONG
        bad = _docker_evaluate(
            _write_synthetic_module(base, "bad-candidate", bad_source),
            base, image_digest,
        )
        hang_source = HANG
        hang = _docker_evaluate(
            _write_synthetic_module(base, "hang-candidate", hang_source),
            base, image_digest, seconds=3,
        )
        passed = (
            good.status == "pass" and bad.status == "fail" and
            hang.status == "timeout" and
            all(c.cleanup_confirmed for c in (good, bad, hang))
        )
        evidence = {
            "contract": "foundation.synthetic-offline-eval/v0",
            "trustLevel": "github-ci-log-unattested",
            "taskId": task.task_id,
            "provider": "synthetic-codex-labelled-fixture-NOT-live-model",
            "modelInvoked": False,
            "approval": "synthetic-test-decision-NOT-human-authenticated",
            "sourceDigest": sha256(fake_model_output.changes[0].content.encode()).hexdigest(),
            "proposalSha256": digest,
            "commit": os.environ.get("GITHUB_SHA"),
            "imageDigest": image_digest,
            "time": datetime.now(timezone.utc).isoformat(),
            "result": "pass" if passed else "fail",
            "checks": {
                "staged-good": asdict(good),
                "negative-wrong-answer": asdict(bad),
                "negative-timeout": asdict(hang),
            },
        }
    dest = ROOT / "artifacts" / "g16-synthetic-offline-eval.json"
    dest.parent.mkdir(exist_ok=True)
    dest.write_text(json.dumps(evidence, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    print(json.dumps({
        "result": evidence["result"],
        "checks": {k:v.status for k,v in (("staged-good",good), ("wrong-answer",bad),("timeout",hang))},
        "modelInvoked": False,
    }))
    return 0 if passed else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    args = parser.parse_args()
    return smoke(args.image)

if __name__ == "__main__":
    sys.exit(main())
