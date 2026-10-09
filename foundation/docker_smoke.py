"""Offline G1.2 CI proof: real Docker checks, no agent/network/secrets."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

from .docker_executor import run_fixture_check, require_disposable_host
from .sandbox import SandboxPolicy

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "tests" / "fixtures" / "offline-sandbox"

def execute(image_digest: str) -> int:
    require_disposable_host()
    policy = SandboxPolicy(image_digest=image_digest, timeout_seconds=50)
    good = run_fixture_check(FIX / "project-good", "python-eval", policy,
                             acceptance_dir=FIX / "acceptance")
    bad = run_fixture_check(FIX / "project-bad", "python-eval", policy,
                            acceptance_dir=FIX / "acceptance")
    invariants = run_fixture_check(FIX / "policy", "python-unit", policy)
    timeout_case = run_fixture_check(FIX / "hang", "python-unit",
                                     SandboxPolicy(image_digest=image_digest, timeout_seconds=4))
    checks = {
        "independent-good": asdict(good),
        "independent-bad": asdict(bad),
        "deny-network-and-writes": asdict(invariants),
        "hard-timeout": asdict(timeout_case),
    }
    expected = (good.status == "pass" and bad.status == "fail" and
                invariants.status == "pass" and timeout_case.status == "timeout")
    # This artifact is not signed, even when produced in CI.
    artifact = {
        "contract": "foundation.offline-sandbox-smoke/v0",
        "trustLevel": "ci-log-not-cryptographic-attestation",
        "source": "github-hosted-ephemeral-runner",
        "commit": os.environ.get("GITHUB_SHA"),
        "imageDigest": image_digest,
        "runnerVersion": "g12/v0",
        "policyHash": hashlib.sha256((ROOT / "foundation/sandbox.py").read_bytes()).hexdigest(),
        "executedAt": datetime.now(timezone.utc).isoformat(),
        "result": "pass" if expected else "fail",
        "checks": checks
    }
    dest = ROOT / "artifacts" / "offline-docker-smoke.json"
    dest.parent.mkdir(exist_ok=True)
    dest.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"result": artifact["result"], "commit": artifact["commit"],
                      "checks": {k: v["status"] for k, v in checks.items()}}))
    return 0 if expected else 1

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True, help="Locally pulled image's resolved repo digest")
    args = parser.parse_args()
    return execute(args.image)

if __name__ == "__main__":
    sys.exit(main())
