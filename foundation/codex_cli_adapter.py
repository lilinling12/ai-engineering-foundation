"""G1.3 Codex CLI adapter contract; NO live agent or shell invocation.

The first verified slice builds a strict, read-only proposal request and validates
Codex final JSON using the same allowlist as the Responses provider. Executing
the plan requires a separately reviewed disposable runtime with scoped credentials
and egress controls. This module deliberately never calls subprocess or shell.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .harness import AuthoritySnapshot, Proposal, TaskRequest
from .model_gateway import MODEL_NAME, OUTPUT_SCHEMA, ModelGatewayError, extract_proposal

CODEX_VERSION = "0.162.1"
PINNED_TOOL = "@openai/codex@" + CODEX_VERSION


@dataclass(frozen=True)
class CodexRequest:
    argv: tuple[str, ...]
    stdin: str
    schema_json: str
    tool_version: str
    execution_status: str = "NOT_EXECUTED"


def build_codex_request(task: TaskRequest, authority: AuthoritySnapshot,
                        *, model: str, worktree: Path,
                        schema_path: Path, result_path: Path,
                        codex_executable: str = "codex") -> CodexRequest:
    """Plan an output-only Codex exec; never invoke or trust its own sandbox.

    Paths must be operator-provisioned in a separate disposable runtime.
    Calling code must not put user secrets or production repos in that runtime.
    """
    if not MODEL_NAME.fullmatch(model):
        raise ModelGatewayError("Invalid model ID")
    if task.task_id != "python-greeting-v0" or task.stack != "python-service":
        raise ModelGatewayError("Only the reviewed greeting fixture is accepted")
    if task.allowed_paths != ("app/greeting.py",):
        raise ModelGatewayError("Unexpected write allowlist")
    if len(authority.digest) != 64 or any(c not in "0123456789abcdef" for c in authority.digest):
        raise ModelGatewayError("Invalid authority digest")
    if codex_executable != "codex":
        raise ModelGatewayError("Arbitrary CLI executable forbidden")
    paths = (worktree, schema_path, result_path)
    if any(not isinstance(p, Path) or not p.is_absolute() or ".." in p.parts for p in paths):
        raise ModelGatewayError("Paths must be absolute and canonical")
    if not worktree.is_dir() or worktree.is_symlink():
        raise ModelGatewayError("Expected dedicated existing workspace")
    if schema_path.parent == worktree or result_path.parent == worktree:
        raise ModelGatewayError("Control and result files must be outside model workspace")
    if schema_path == result_path or schema_path.exists() or result_path.exists():
        raise ModelGatewayError("Control/result output paths must not pre-exist")
    if not schema_path.parent.is_dir() or not result_path.parent.is_dir():
        raise ModelGatewayError("Missing control/output parent")
    prompt = json.dumps({
        "taskId": task.task_id,
        "objective": task.objective,
        "allowedPaths": list(task.allowed_paths),
        "authorityDigest": authority.digest,
        "authority": {"entry": authority.entrypoint[:1000], "handoff": authority.handoff[:1000]},
        "constraints": [
            "Output exactly one JSON proposal matching the provided schema",
            "Do not change files or request tool execution",
            "Never execute code; this is an untrusted data proposal only",
        ],
    }, ensure_ascii=False, sort_keys=True)
    if len(prompt.encode("utf-8")) > 7000:
        raise ModelGatewayError("Codex input exceeded budget")
    # Codex' own sandbox flags are defense in depth, NOT host-level isolation.
    argv = (
        "codex", "exec", "--sandbox", "read-only",
        "--ephemeral", "--ignore-user-config",
        "--skip-git-repo-check", "--model", model,
        "--cd", str(worktree),
        "--output-schema", str(schema_path),
        "--output-last-message", str(result_path),
        "-",
    )
    return CodexRequest(argv, prompt, json.dumps(OUTPUT_SCHEMA, ensure_ascii=False, sort_keys=True),
                        CODEX_VERSION)


def validate_codex_final_text(raw: str, task: TaskRequest) -> Proposal:
    """Validate JSON data only; never import, evaluate, apply or execute source."""
    if not isinstance(raw, str) or len(raw.encode("utf-8")) > 80000:
        raise ModelGatewayError("Codex final message is invalid or oversized")
    envelope: dict[str, Any] = {
        "status": "completed",
        "output": [{
            "type": "message", "role": "assistant",
            "content": [{"type": "output_text", "text": raw}],
        }],
    }
    return extract_proposal(envelope, task.allowed_paths)
