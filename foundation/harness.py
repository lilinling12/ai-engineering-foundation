"""Offline Agent Harness golden path.

Only built-in fixtures may produce changes. This is not a sandbox nor a real
model provider; arbitrary project code is NOT safe to evaluate here.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tempfile
from typing import Protocol

from .__main__ import init_project, verify_project

ROOT = Path(__file__).resolve().parent.parent
DEMO_TASK = ROOT / "examples" / "tasks" / "python-greeting.json"
TASK_CONTRACT = "foundation.task/v0"
EVIDENCE_CONTRACT = "foundation.agent-run/v0"

class PolicyError(ValueError):
    """Reject an unauthorized task, provider, or filesystem change."""

@dataclass(frozen=True)
class TaskRequest:
    task_id: str
    stack: str
    objective: str
    allowed_paths: tuple[str, ...]
    acceptance_id: str

@dataclass(frozen=True)
class AuthoritySnapshot:
    digest: str
    entrypoint: str
    handoff: str

@dataclass(frozen=True)
class Change:
    path: str
    content: str

@dataclass(frozen=True)
class Proposal:
    summary: str
    changes: tuple[Change, ...]

class AgentProvider(Protocol):
    """Adapter contract for future AI providers; this phase registers fixtures only."""
    id: str
    def propose(self, task: TaskRequest, authority: AuthoritySnapshot) -> Proposal: ...

class FixtureProvider:
    def __init__(self, provider_id: str) -> None:
        if provider_id not in {"fixture-pass", "fixture-fail"}:
            raise PolicyError("Only offline fixture providers are supported; no model is invoked")
        self.id = provider_id

    def propose(self, task: TaskRequest, authority: AuthoritySnapshot) -> Proposal:
        if task.task_id != "python-greeting-v0" or not authority.digest:
            raise PolicyError("Unsupported fixture task")
        greeting = "Hello" if self.id == "fixture-pass" else "Wrong"
        source = f'def greet(name: str) -> str:\n    return "{greeting}, " + name\n'
        return Proposal(summary="Fixture proposes a single application file",
                        changes=(Change(path="app/greeting.py", content=source),))

def _relative_path(path: str) -> bool:
    if not isinstance(path, str) or len(path) > 160 or not path or "\\" in path or ":" in path:
        return False
    p = PurePosixPath(path)
    return not p.is_absolute() and all(x not in {"", ".", ".."} for x in path.split("/"))

def load_task(path: Path) -> TaskRequest:
    obj = json.loads(path.read_text(encoding="utf-8"))
    required = {"contract", "id", "stack", "objective", "allowedPaths", "acceptanceId"}
    if not isinstance(obj, dict) or set(obj) != required or obj["contract"] != TASK_CONTRACT:
        raise PolicyError("Unexpected task contract or fields")
    if (obj["id"] != "python-greeting-v0" or obj["stack"] != "python-service" or
            obj["acceptanceId"] != "python-greeting/v0" or
            obj["allowedPaths"] != ["app/greeting.py"]):
        raise PolicyError("Task is not part of the signed-off fixture acceptance registry")
    objective = obj["objective"]
    if not isinstance(objective, str) or not (10 <= len(objective) <= 600):
        raise PolicyError("Invalid task objective")
    return TaskRequest(task_id=obj["id"], stack=obj["stack"], objective=objective,
                       allowed_paths=tuple(obj["allowedPaths"]), acceptance_id=obj["acceptanceId"])

def restore_authority(workspace: Path) -> AuthoritySnapshot:
    entry = (workspace / "AGENTS.md").read_text(encoding="utf-8")
    handoff = (workspace / "docs/handoff/CURRENT.md").read_text(encoding="utf-8")
    if not entry or not handoff:
        raise PolicyError("Missing authoritative entrypoint or handoff")
    return AuthoritySnapshot(sha256((entry + "\n" + handoff).encode()).hexdigest(), entry, handoff)

def apply_proposal(workspace: Path, proposal: Proposal, allowed_paths: tuple[str, ...]) -> None:
    if not proposal.changes:
        raise PolicyError("Empty proposal")
    seen: set[str] = set()
    root = workspace.resolve()
    for change in proposal.changes:
        if (not _relative_path(change.path) or change.path not in allowed_paths or
                change.path in seen):
            raise PolicyError("Provider attempted an unauthorized file change")
        seen.add(change.path)
        target = workspace / change.path
        if not target.resolve().is_relative_to(root):
            raise PolicyError("Proposal path escapes workspace")
        if not isinstance(change.content, str) or len(change.content.encode()) > 64_000:
            raise PolicyError("Invalid content size")
    # Only apply after the entire proposal has passed validation.
    for change in proposal.changes:
        target = workspace / change.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(change.content, encoding="utf-8")

def independent_evaluation(workspace: Path, acceptance_id: str) -> dict:
    if acceptance_id != "python-greeting/v0":
        raise PolicyError("Unknown independent acceptance suite")
    # Check definition is in foundation source, NOT in the provider proposal.
    assertion = (
        "from app.greeting import greet\n"
        "assert greet('Ada') == 'Hello, Ada'\n"
        "assert greet('') == 'Hello, '\n"
        "assert greet('世界') == 'Hello, 世界'\n"
    )
    try:
        completed = subprocess.run(
            [sys.executable, "-B", "-c", assertion], cwd=workspace,
            capture_output=True, text=True, timeout=10, check=False)
        return {"id": acceptance_id, "result": "pass" if completed.returncode == 0 else "fail",
                "exitCode": completed.returncode, "outputTail": (completed.stdout + completed.stderr)[-2000:]}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"id": acceptance_id, "result": "fail", "exitCode": 1, "outputTail": str(exc)}

def run_demo(destination: Path, task_path: Path | None = None, provider_id: str = "fixture-pass") -> bool:
    """Run one trusted demo request in an independent temporary workspace.

    The temporary copy is NOT a security sandbox. Only built-in fixture providers
    are supported; explicit arbitrary-agent execution is deliberately denied.
    """
    task = load_task(task_path or DEMO_TASK)
    provider: AgentProvider = FixtureProvider(provider_id)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"Refusing to overwrite: {destination}")
    with tempfile.TemporaryDirectory(prefix="foundation-agent-") as scratch:
        work = Path(scratch) / "workspace"
        init_project(task.stack, work)
        authority = restore_authority(work)
        checks: list[dict] = []
        try:
            proposal = provider.propose(task, authority)
            apply_proposal(work, proposal, task.allowed_paths)
            checks.append({"id": "policy", "result": "pass"})
            verified = verify_project(work)
            checks.append({"id": "stack-verification", "result": "pass" if verified else "fail"})
            checks.append(independent_evaluation(work, task.acceptance_id))
        except PolicyError as exc:
            checks.append({"id": "policy", "result": "fail", "reason": str(exc)})
        passed = all(item["result"] == "pass" for item in checks)
        evidence = {
            "contract": EVIDENCE_CONTRACT,
            "taskId": task.task_id,
            "stack": task.stack,
            "provider": provider.id,
            "authorityDigest": authority.digest,
            "taskDigest": sha256(json.dumps({
                "id": task.task_id, "stack": task.stack, "objective": task.objective,
                "paths": task.allowed_paths, "acceptance": task.acceptance_id
            }, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "executionBoundary": "temporary-workspace-only-NOT-sandbox",
            "trustLevel": "local-unattested",
            "result": "pass" if passed else "fail",
            "checks": checks
        }
        shutil.copytree(work, destination)
        (destination / ".foundation" / "agent-evidence.json").write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"result": evidence["result"], "provider": provider.id,
                          "evidence": str(destination / ".foundation" / "agent-evidence.json"),
                          "checks": [{"id": c["id"], "result": c["result"]} for c in checks]}))
        return passed

if __name__ == "__main__":
    raise SystemExit("Use python -m foundation agent-demo --dest PATH")
