"""Opt-in G1.5 Codex CLI process invocation for a fixed synthetic task.

This is a DEVELOPERS-ONLY local/disposable-host experiment, not hardened
isolation. Codex CLI can run local tools and an API credential passed into its
process may be readable by child processes. Never run this on production hosts,
against private repositories, or with long-lived credentials.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Callable, Any

from .__main__ import ROOT, init_project
from .codex_cli_adapter import CODEX_VERSION, build_codex_request, validate_codex_final_text
from .harness import DEMO_TASK, load_task, restore_authority
from .model_gateway import MODEL_NAME, ModelGatewayError, _write_quarantine

MAX_INFERENCE_SECONDS = 180
VERSION_RE = re.compile(r"^codex-cli " + re.escape(CODEX_VERSION) + r"$")

Runner = Callable[..., Any]


@dataclass(frozen=True)
class CodexMetadata:
    id: str
    model: str


def _cli_binary() -> Path:
    """Use only the locally installed, lockfile-backed CLI for this project."""
    suffix = "codex.cmd" if os.name == "nt" else "codex"
    binary = ROOT / "tools" / "codex-cli" / "node_modules" / ".bin" / suffix
    if not binary.is_file():
        raise ModelGatewayError(
            "Pinned Codex binary missing; run npm ci --ignore-scripts "
            "in tools/codex-cli on a trusted, disposable machine"
        )
    return binary.resolve()


def _minimized_env(scratch: Path, api_key: str) -> dict[str, str]:
    if not api_key or "\r" in api_key or "\n" in api_key:
        raise ModelGatewayError("Missing or invalid OPENAI_API_KEY")
    env: dict[str, str] = {
        "OPENAI_API_KEY": api_key,
        "CODEX_HOME": str(scratch / "codex-home"),
        "HOME": str(scratch / "home"),
        "TMPDIR": str(scratch / "tmp"),
        "TMP": str(scratch / "tmp"),
        "TEMP": str(scratch / "tmp"),
        "PATH": os.environ.get("PATH", ""),
    }
    # Needed by Windows process loading. Do not copy other ambient variables.
    if os.name == "nt":
        for key in ("SYSTEMROOT", "WINDIR", "PATHEXT"):
            if os.environ.get(key):
                env[key] = os.environ[key]
    return env


def run_codex_fixture(
    destination: Path, model: str, *, paid_opt_in: bool,
    risk_acknowledged: bool, runner: Runner = subprocess.run,
    cli_binary: Path | None = None, api_key: str | None = None,
) -> Path:
    """Call the real Codex process only when all manual gates are set.

    Tests inject a fake subprocess runner. No model calls happen in CI.
    """
    if not paid_opt_in or not risk_acknowledged:
        raise ModelGatewayError(
            "Real inference requires --permit-paid-inference and "
            "--acknowledge-local-runtime-risk"
        )
    if os.environ.get("FOUNDATION_DISPOSABLE_RUNTIME") != "yes":
        raise ModelGatewayError("Only explicit disposable-runtime experiments are allowed")
    if not MODEL_NAME.fullmatch(model):
        raise ModelGatewayError("Invalid model ID")
    token = api_key if api_key is not None else os.environ.get("OPENAI_API_KEY")
    if not token:
        raise ModelGatewayError("OPENAI_API_KEY required (temporary, scoped key only)")
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("Quarantine destination already exists")
    if not destination.parent.is_dir() or destination.parent.is_symlink():
        raise ModelGatewayError("Quarantine parent must exist")

    # Absolutely no customer, external repo, or uploaded source is brought in.
    task = load_task(DEMO_TASK)
    binary = cli_binary or _cli_binary()
    if not binary.is_absolute() or not binary.is_file() or binary.is_symlink():
        raise ModelGatewayError("Expected an installed, trusted absolute Codex CLI binary")

    with tempfile.TemporaryDirectory(prefix="foundation-codex-live-") as td:
        scratch = Path(td)
        work = scratch / "synthetic-workspace"
        control = scratch / "control"
        control.mkdir()
        for folder in ("home", "codex-home", "tmp"):
            (scratch / folder).mkdir()
        init_project(task.stack, work)
        authority = restore_authority(work)
        schema = control / "schema.json"
        result = control / "last-message.json"
        plan = build_codex_request(
            task, authority, model=model, worktree=work,
            schema_path=schema, result_path=result,
        )
        schema.write_text(plan.schema_json, encoding="utf-8")
        args = [str(binary), *plan.argv[1:]]
        env = _minimized_env(scratch, token)
        try:
            version = runner(
                [str(binary), "--version"], cwd=work, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, timeout=12, check=False,
            )
            if version.returncode != 0 or not VERSION_RE.fullmatch((version.stdout or "").strip()):
                raise ModelGatewayError("Installed Codex version does not match pinned tool")
            completed = runner(
                args, cwd=work, env=env, input=plan.stdin,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                text=True, timeout=MAX_INFERENCE_SECONDS, check=False,
            )
        except subprocess.TimeoutExpired:
            raise ModelGatewayError("Codex run timed out; descendant process cleanup unverified") from None
        except (OSError, subprocess.SubprocessError):
            raise ModelGatewayError("Codex process unavailable or could not finish") from None
        if completed.returncode != 0:
            raise ModelGatewayError(f"Codex failed with exit status {completed.returncode}")
        if result.is_symlink() or not result.is_file() or result.stat().st_size > 80_000:
            raise ModelGatewayError("Codex final structured output missing or oversized")
        proposal = validate_codex_final_text(result.read_text(encoding="utf-8"), task)
        # Never copy generated source into executable project trees.
        return _write_quarantine(
            destination, task, authority,
            CodexMetadata(id="codex-cli", model=model), proposal,
        )


def codex_propose(destination: Path, model: str, paid_opt_in: bool,
                  risk_acknowledged: bool) -> int:
    evidence = run_codex_fixture(
        destination, model, paid_opt_in=paid_opt_in,
        risk_acknowledged=risk_acknowledged,
    )
    print(json.dumps({
        "status": "pending-review", "provider": "codex-cli",
        "modelExecuted": True, "generatedCodeExecuted": False,
        "evidence": str(evidence), "attested": False,
    }))
    return 0
