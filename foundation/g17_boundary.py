"""G1.7: synthetic-only safety checks; NOT an untrusted-code sandbox."""
from __future__ import annotations

import json
import os
from pathlib import Path

from .__main__ import ROOT
from .sandbox import SandboxPolicyError

GOOD = 'def greet(name: str) -> str:\n    return "Hello, " + name\n'
WRONG = 'def greet(name: str) -> str:\n    return "Wrong, " + name\n'
HANG = 'import time\ntime.sleep(30)\ndef greet(name: str) -> str:\n    return "Hello, " + name\n'
KNOWN = {"staged": GOOD, "bad-candidate": WRONG, "hang-candidate": HANG}
TEMPLATE = ROOT / "templates" / "python-service"
ACCEPTANCE = ROOT / "tests" / "fixtures" / "offline-sandbox" / "acceptance"
ORACLE_TEXT = (
    'import unittest\n'
    'from app.greeting import greet\n'
    '\n'
    'class IndependentAcceptance(unittest.TestCase):\n'
    '    def test_greeting(self):\n'
    '        self.assertEqual(greet("Ada"), "Hello, Ada")\n'
    '        self.assertEqual(greet("世界"), "Hello, 世界")\n'
)


def require_synthetic_candidate(root: Path) -> None:
    if root.name not in KNOWN or not root.is_dir() or root.is_symlink():
        raise SandboxPolicyError("Not a built-in synthetic candidate")
    candidate = root / "app" / "greeting.py"
    if candidate.is_symlink() or not candidate.is_file() or candidate.stat().st_size > 512:
        raise SandboxPolicyError("Synthetic source missing/unsafe")
    if candidate.read_text(encoding="utf-8") != KNOWN[root.name]:
        raise SandboxPolicyError("Candidate source differs from built-in fixture")
    if root.name == "staged":
        expected_py = {"app/__init__.py", "app/core.py",
                       "app/greeting.py", "tests/test_core.py"}
        evidence = root / ".foundation" / "stage-evidence.json"
        marker = root / ".foundation" / "UNTRUSTED_DO_NOT_EXECUTE"
        if (evidence.is_symlink() or marker.is_symlink() or
                not evidence.is_file() or not marker.is_file()):
            raise SandboxPolicyError("Missing synthetic staging evidence or marker")
        try:
            obj = json.loads(evidence.read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeError):
            raise SandboxPolicyError("Invalid staging evidence") from None
        if (obj.get("contract") != "foundation.static-stage/v0" or
                obj.get("executed") is not False or
                obj.get("result") != "static-accepted-not-executed"):
            raise SandboxPolicyError("Unexpected staging state")
        for name in ("app/__init__.py", "app/core.py", "tests/test_core.py"):
            actual = root / name
            original = TEMPLATE / name
            if (actual.is_symlink() or not actual.is_file() or
                    actual.read_bytes() != original.read_bytes()):
                raise SandboxPolicyError("Scaffold Python changed outside proposal")
    else:
        expected_py = {"app/__init__.py", "app/greeting.py"}
        initializer = root / "app" / "__init__.py"
        if (initializer.is_symlink() or not initializer.is_file() or
                initializer.read_bytes()):
            raise SandboxPolicyError("Unexpected synthetic Python initializer")
    present_py: set[str] = set()
    for p in root.rglob("*"):
        if p.is_symlink():
            raise SandboxPolicyError("Candidate tree contains symlink")
        if p.is_file() and p.suffix == ".py":
            present_py.add(p.relative_to(root).as_posix())
    if present_py != expected_py:
        raise SandboxPolicyError("Unreviewed Python source in candidate")


def require_reviewed_oracle() -> None:
    if ACCEPTANCE.is_symlink() or not ACCEPTANCE.is_dir():
        raise SandboxPolicyError("Missing independent acceptance oracle")
    paths = tuple(ACCEPTANCE.iterdir())
    if (len(paths) != 1 or paths[0].name != "test_greeting.py" or
            paths[0].is_symlink() or not paths[0].is_file() or
            paths[0].read_text(encoding="utf-8") != ORACLE_TEXT):
        raise SandboxPolicyError("Independent oracle differs from reviewed source")


def isolated_docker_env(root: Path) -> dict[str, str]:
    if root.is_symlink() or not root.is_dir():
        raise SandboxPolicyError("Invalid disposable workspace")
    home = root / ".docker-client-home"
    if home.is_symlink():
        raise SandboxPolicyError("Symlinked Docker configuration directory")
    home.mkdir(mode=0o700, exist_ok=True)
    if home.is_symlink() or not home.is_dir():
        raise SandboxPolicyError("Invalid Docker client home")
    # Drop all ambient secrets (GITHUB_TOKEN, ACTIONS_RUNTIME_TOKEN, OPENAI_*, AWS_*),
    # proxies, and remote Docker daemon selectors (DOCKER_HOST/DOCKER_CONTEXT).
    return {"PATH": os.defpath, "HOME": str(home), "LANG": "C.UTF-8"}
