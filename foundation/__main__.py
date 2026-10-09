"""Small trusted-local CLI. Does not sandbox or execute third-party manifests."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "stack-packs" / "catalog.json"
TEMPLATES = ROOT / "templates"
CONTRACT = "foundation.project/v0"

# Trusted, code-owned commands. The project manifest may select a known pack
# but MUST NOT supply executable commands.
CHECKS = {
    "python-service": [
        ("unit-test", lambda: [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])
    ],
    "typescript-api": [
        ("typecheck", lambda: ["npm", "run", "typecheck"]),
        ("test", lambda: ["npm", "test"]),
        ("build", lambda: ["npm", "run", "build"])
    ],
}

def catalog() -> dict:
    obj = json.loads(CATALOG.read_text(encoding="utf-8"))
    if obj.get("contract") != "foundation.stack-packs/v0":
        raise ValueError("Unsupported stack catalog")
    ids = [p["id"] for p in obj["packs"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate stack id")
    return {p["id"]: p for p in obj["packs"]}

def init_project(stack: str, dest: Path) -> None:
    packs = catalog()
    if stack not in packs or packs[stack]["status"] != "runnable":
        raise ValueError(f"Stack {stack!r} is not scaffoldable; run 'catalog'")
    source = TEMPLATES / stack
    if not source.is_dir():
        raise ValueError("Trusted template missing")
    if dest.exists() or dest.is_symlink():
        raise FileExistsError(f"Refusing to overwrite: {dest}")
    shutil.copytree(source, dest)
    metadata = dest / ".foundation"
    metadata.mkdir()
    (metadata / "project.json").write_text(
        json.dumps({"contract": CONTRACT, "stack": stack, "scaffoldVersion": "0.1.0"}, indent=2) + "\n",
        encoding="utf-8"
    )
    (dest / "AGENTS.md").write_text(
        "# Project agent entrypoint\nRead docs/handoff/CURRENT.md and project domain authority first. "
        "Check Git live state. Never claim local verification as CI attestation.\n", encoding="utf-8"
    )
    handoff = dest / "docs" / "handoff"
    handoff.mkdir(parents=True)
    (handoff / "CURRENT.md").write_text(
        "# Current\nNew project scaffold. Domain authority, security policy and production "
        "requirements must be authored before implementation.\n", encoding="utf-8"
    )

def git_head(project: Path) -> str | None:
    if not (project / ".git").exists():
        return None
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=project,
                                capture_output=True, text=True, timeout=10, check=True)
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None

def verify_project(project: Path) -> bool:
    untrusted_marker = project / ".foundation" / "UNTRUSTED_DO_NOT_EXECUTE"
    if untrusted_marker.exists() or untrusted_marker.is_symlink():
        raise ValueError("Untrusted staged source must not run in trusted-local verifier")
    manifest = project / ".foundation" / "project.json"
    obj = json.loads(manifest.read_text(encoding="utf-8"))
    if (not isinstance(obj, dict) or
            set(obj) != {"contract", "stack", "scaffoldVersion"} or
            obj["contract"] != CONTRACT or obj["scaffoldVersion"] != "0.1.0"):
        raise ValueError("Invalid project manifest contract")
    pack = obj["stack"]
    if pack not in CHECKS or catalog()[pack]["status"] != "runnable":
        raise ValueError("Unknown or unsupported stack")
    checks = []
    all_ok = True
    for name, command_factory in CHECKS[pack]:
        argv = command_factory()
        try:
            # Never persist raw subprocess output into reviewable evidence.
            # Test logs may contain credentials, patient data, or other secrets.
            run = subprocess.run(
                argv, cwd=project, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, timeout=180, check=False
            )
            code = run.returncode
            failure_kind = "none" if code == 0 else "check-failed"
        except subprocess.TimeoutExpired:
            code, failure_kind = 124, "timeout"
        except OSError:
            code, failure_kind = 127, "spawn-error"
        checks.append({"id": name, "result": "pass" if code == 0 else "fail",
                       "exitCode": code, "failureKind": failure_kind,
                       "outputTail": "[redacted; command output is never persisted]"})
        all_ok = all_ok and code == 0
    evidence = {
        "contract": "foundation.evidence/v0", "stack": pack,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "gitHead": git_head(project),
        "trustLevel": "local-unattested",
        "result": "pass" if all_ok else "fail", "checks": checks
    }
    evidence_path = project / ".foundation" / "evidence.json"
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
    print(json.dumps({"result": evidence["result"], "evidence": str(evidence_path),
                      "checks": [{"id": c["id"], "result": c["result"]} for c in checks]}))
    return all_ok

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="foundation")
    subs = parser.add_subparsers(dest="command", required=True)
    subs.add_parser("catalog")
    init = subs.add_parser("init")
    init.add_argument("--stack", required=True)
    init.add_argument("--dest", type=Path, required=True)
    verify = subs.add_parser("verify")
    verify.add_argument("--project", type=Path, required=True)
    verify.add_argument("--trust-project-code", action="store_true",
                        help="Acknowledge that project tests and npm scripts execute LOCAL code; NOT a sandbox")
    args = parser.parse_args(argv)
    try:
        if args.command == "catalog":
            print(json.dumps(list(catalog().values()), ensure_ascii=False, indent=2))
        elif args.command == "init":
            init_project(args.stack, args.dest)
            print(f"Initialized {args.stack}: {args.dest}")
        elif args.command == "verify":
            if not args.trust_project_code:
                raise ValueError("Local project checks execute code. Pass --trust-project-code only for trusted local projects; this is NOT a sandbox")
            return 0 if verify_project(args.project.resolve()) else 1
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"foundation: {exc}", file=sys.stderr)
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

