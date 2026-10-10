"""G1.4 local approval and independent STATIC acceptance, with zero code execution.

Only the built-in greeting task is supported. A local approval is NOT an
authenticated or cryptographically signed human authorization.
"""
from __future__ import annotations

import ast
from datetime import datetime, timezone, timedelta
from hashlib import sha256
import hmac
import json
from pathlib import Path
import tempfile
from typing import Any

from .__main__ import init_project
from .harness import Change, DEMO_TASK, Proposal, apply_proposal, load_task, restore_authority
from .model_gateway import CONTRACT as PROPOSAL_CONTRACT

APPROVAL_CONTRACT = "foundation.local-decision/v0"
STAGED_CONTRACT = "foundation.static-stage/v0"
SHA_SIZE = 64
MAX_AGE = timedelta(minutes=30)

class ReviewGateError(ValueError):
    pass


def _json_file(path: Path, byte_limit: int = 120_000) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > byte_limit:
        raise ReviewGateError("Missing, symlinked or oversized review file")
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, ValueError, OSError):
        raise ReviewGateError("Invalid review file JSON") from None
    if not isinstance(obj, dict):
        raise ReviewGateError("Review file must be an object")
    return obj


def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _equals(left: str, right: str) -> bool:
    return isinstance(left, str) and isinstance(right, str) and hmac.compare_digest(left, right)


def _sha(value: str) -> bool:
    return isinstance(value, str) and len(value) == SHA_SIZE and all(c in "0123456789abcdef" for c in value)


def read_quarantine(directory: Path) -> tuple[dict[str, Any], str]:
    """Verify original proposal and evidence bytes as a pair.

    SHA detects accidental or post-review modification; a forged JSON pair is
    possible because this stage has no authenticated issuer.
    """
    if directory.is_symlink() or not directory.is_dir():
        raise ReviewGateError("Expected an existing non-symlink quarantine directory")
    proposal = _json_file(directory / "proposal.json")
    evidence = _json_file(directory / "evidence.json")
    digest = sha256(_canonical(proposal)).hexdigest()
    fields = {"contract", "provider", "model", "taskId", "authorityDigest", "summary", "changes"}
    if set(proposal) != fields or proposal.get("contract") != PROPOSAL_CONTRACT:
        raise ReviewGateError("Unexpected proposal contract")
    if proposal.get("provider") not in {"openai-responses", "codex-cli"}:
        raise ReviewGateError("Untrusted provider")
    if not isinstance(proposal.get("model"), str) or not (3 <= len(proposal["model"]) <= 80):
        raise ReviewGateError("Unexpected model field")
    if proposal.get("taskId") != "python-greeting-v0" or not _sha(proposal.get("authorityDigest")):
        raise ReviewGateError("Task / authority not supported")
    if not isinstance(proposal.get("summary"), str) or not (1 <= len(proposal["summary"]) <= 500):
        raise ReviewGateError("Malformed summary")
    changes = proposal.get("changes")
    if not isinstance(changes, list) or len(changes) != 1 or not isinstance(changes[0], dict):
        raise ReviewGateError("Only one restricted fixture change is supported")
    item = changes[0]
    if set(item) != {"path", "content"} or item["path"] != "app/greeting.py":
        raise ReviewGateError("Proposal changed an unauthorized path")
    if not isinstance(item["content"], str) or not (0 < len(item["content"].encode("utf-8")) <= 64000):
        raise ReviewGateError("Invalid content or code budget")
    if "\x00" in item["content"]:
        raise ReviewGateError("Source contains NUL")
    required_evidence = {
        "contract", "provider", "model", "taskId", "authorityDigest",
        "proposalSha256", "timestamp", "result", "applied", "executed", "trustLevel"
    }
    if set(evidence) != required_evidence or evidence.get("contract") != "foundation.proposal-evidence/v0":
        raise ReviewGateError("Unexpected proposal evidence")
    if not (_equals(evidence.get("proposalSha256"), digest)
            and evidence.get("taskId") == proposal["taskId"]
            and evidence.get("authorityDigest") == proposal["authorityDigest"]
            and evidence.get("provider") == proposal["provider"]
            and evidence.get("model") == proposal["model"]
            and evidence.get("result") == "pending-review"
            and evidence.get("applied") is False
            and evidence.get("executed") is False
            and evidence.get("trustLevel") == "local-unattested"):
        raise ReviewGateError("Proposal/evidence mismatch, or proposal already marked executed")
    return proposal, digest


def record_decision(quarantine: Path, confirm_sha: str, decision: str, dest: Path) -> Path:
    """Requires operator to explicitly submit the full 64-character digest."""
    proposal, digest = read_quarantine(quarantine)
    if not _sha(confirm_sha) or not _equals(digest, confirm_sha):
        raise ReviewGateError("Explicit full proposal SHA-256 confirmation does not match")
    if decision not in {"approve", "reject"}:
        raise ReviewGateError("Invalid decision")
    if dest.exists() or dest.is_symlink():
        raise FileExistsError("Decision path already exists")
    decision_record = {
        "contract": APPROVAL_CONTRACT,
        "decision": decision,
        "proposalSha256": digest,
        "taskId": proposal["taskId"],
        "authorityDigest": proposal["authorityDigest"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "trustLevel": "local-unattested-no-authentication",
    }
    # Exclusive creation avoids overwriting another operator's record.
    with dest.open("x", encoding="utf-8") as out:
        out.write(json.dumps(decision_record, indent=2, ensure_ascii=False) + "\n")
    return dest


def _parse_time(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ReviewGateError("Invalid decision timestamp")
    try:
        date = datetime.fromisoformat(value)
    except ValueError:
        raise ReviewGateError("Invalid decision timestamp") from None
    if date.tzinfo is None or date.utcoffset() is None:
        raise ReviewGateError("Decision timestamp must be timezone-aware")
    return date.astimezone(timezone.utc)


def verify_decision(proposal: dict[str, Any], digest: str, path: Path) -> dict[str, Any]:
    decision = _json_file(path, 10_000)
    required = {"contract", "decision", "proposalSha256", "taskId", "authorityDigest", "timestamp", "trustLevel"}
    if set(decision) != required or decision["contract"] != APPROVAL_CONTRACT:
        raise ReviewGateError("Unexpected local decision schema")
    if (decision.get("decision") != "approve"
            or decision.get("trustLevel") != "local-unattested-no-authentication"
            or not _equals(decision.get("proposalSha256"), digest)
            or decision.get("taskId") != proposal["taskId"]
            or decision.get("authorityDigest") != proposal["authorityDigest"]):
        raise ReviewGateError("Decision missing, rejected or bound to another proposal")
    age = datetime.now(timezone.utc) - _parse_time(decision["timestamp"])
    if not timedelta(seconds=-120) <= age <= MAX_AGE:
        raise ReviewGateError("Decision expired or from the future")
    return decision


def static_accept_greeting(source: str) -> dict[str, Any]:
    """Check one fixed pure expression using AST only; NEVER import/eval/exec source.

    Deliberately narrow: only the exact reference expression is accepted.
    This is not a general-purpose Python correctness or security verifier.
    """
    try:
        tree = ast.parse(source, filename="untrusted-greeting.py")
    except (SyntaxError, ValueError, TypeError):
        return {"id": "python-greeting-static/v0", "result": "fail", "reason": "syntax"}
    if len(tree.body) != 1 or type(tree.body[0]) is not ast.FunctionDef:
        return {"id": "python-greeting-static/v0", "result": "fail", "reason": "top-level"}
    fn = tree.body[0]
    args = fn.args
    shape = (fn.name == "greet" and not fn.decorator_list and
             not getattr(fn, "type_params", ()) and
             len(args.posonlyargs) == 0 and len(args.args) == 1 and
             len(args.kwonlyargs) == 0 and not args.defaults and
             not args.kw_defaults and args.vararg is None and args.kwarg is None and
             args.args[0].arg == "name" and type(args.args[0].annotation) is ast.Name and
             args.args[0].annotation.id == "str" and
             type(fn.returns) is ast.Name and fn.returns.id == "str" and
             len(fn.body) == 1 and type(fn.body[0]) is ast.Return)
    if not shape:
        return {"id": "python-greeting-static/v0", "result": "fail", "reason": "function-shape"}
    result = fn.body[0].value
    valid = (type(result) is ast.BinOp and type(result.op) is ast.Add and
             type(result.left) is ast.Constant and result.left.value == "Hello, " and
             type(result.right) is ast.Name and result.right.id == "name")
    return {"id": "python-greeting-static/v0", "result": "pass" if valid else "fail",
            "reason": "exact-pure-expression" if valid else "expression-not-allowed"}


def stage_reviewed_proposal(quarantine: Path, approval_file: Path, dest: Path) -> Path:
    """Stage approved model source in a fresh, explicitly UNTRUSTED directory.

    No Python code is run, imported or compiled, and no existing project is
    modified. Generic 'foundation verify' is disabled on staged directories.
    """
    proposal, digest = read_quarantine(quarantine)
    verify_decision(proposal, digest, approval_file)
    if dest.exists() or dest.is_symlink():
        raise FileExistsError("Staging destination already exists")
    if not dest.parent.is_dir() or dest.parent.is_symlink():
        raise ReviewGateError("Destination parent must be an existing direct directory")
    source = proposal["changes"][0]["content"]
    acceptance = static_accept_greeting(source)
    if acceptance["result"] != "pass":
        raise ReviewGateError("Independent static acceptance failed: " + acceptance["reason"])
    task = load_task(DEMO_TASK)
    with tempfile.TemporaryDirectory(prefix=".foundation-stage-", dir=dest.parent) as tmp:
        work = Path(tmp) / "project"
        init_project(task.stack, work)
        current_authority = restore_authority(work)
        if not _equals(current_authority.digest, proposal["authorityDigest"]):
            raise ReviewGateError("Authority snapshot changed since model inference")
        apply_proposal(work, Proposal(proposal["summary"], (Change("app/greeting.py", source),)),
                       task.allowed_paths)
        # Marker blocks generic verify CLI, which otherwise executes project code locally.
        (work / ".foundation" / "UNTRUSTED_DO_NOT_EXECUTE").write_text(
            "Model-generated code: NOT approved for execution. No sandbox attestation.\n", encoding="utf-8")
        applied_evidence = {
            "contract": STAGED_CONTRACT,
            "proposalSha256": digest,
            "decisionSha256": sha256(approval_file.read_bytes()).hexdigest(),
            "authorityDigest": current_authority.digest,
            "result": "static-accepted-not-executed",
            "staticCheck": acceptance,
            "appliedTo": "new-disposable-workspace-only",
            "executed": False,
            "trustLevel": "local-unattested-no-authentication",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        (work / ".foundation" / "stage-evidence.json").write_text(
            json.dumps(applied_evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        work.rename(dest)
    return dest / ".foundation" / "stage-evidence.json"
