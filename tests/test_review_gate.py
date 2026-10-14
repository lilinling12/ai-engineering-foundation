import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from hashlib import sha256

from foundation.__main__ import verify_project, main
from foundation.harness import DEMO_TASK, load_task, restore_authority, Proposal, Change
from foundation.__main__ import init_project
from foundation.codex_live import CodexMetadata
from foundation.model_gateway import _write_quarantine
from foundation.model_gateway import OpenAIProposalProvider, propose_fixture
from foundation.review_gate import (
    ReviewGateError, read_quarantine, record_decision, stage_reviewed_proposal,
    static_accept_greeting, verify_decision,
)

GOOD = "def greet(name: str) -> str:\n    return 'Hello, ' + name\n"
BAD = "def greet(name: str) -> str:\n    return 'Wrong, ' + name\n"
MALICIOUS = "import os\nos.system('echo should-not-run')\ndef greet(name: str) -> str:\n    return 'Hello, ' + name\n"

def fake_response(source: str) -> dict:
    result = {"summary": "Fixture greeting", "changes": [{"path": "app/greeting.py", "content": source}]}
    return {"status": "completed", "output": [{"type": "message", "role": "assistant",
            "content": [{"type": "output_text", "text": json.dumps(result)}]}]}

def prepare(root: Path, code: str = GOOD):
    provider = OpenAIProposalProvider("test-model", "local-test-token",
                                      lambda *_: fake_response(code))
    quarantine = root / "quarantine"
    propose_fixture(None, provider, quarantine)
    sha = read_quarantine(quarantine)[1]
    return quarantine, sha

class ReviewGateTests(unittest.TestCase):
    def test_approved_to_staged_only_without_execution(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            quarantine, digest = prepare(root)
            receipt = record_decision(quarantine, digest, "approve", root / "decision.json")
            path = stage_reviewed_proposal(quarantine, receipt, root / "staged")
            ev = json.loads(path.read_text())
            self.assertEqual(ev["result"], "static-accepted-not-executed")
            self.assertFalse(ev["executed"])
            self.assertEqual(ev["proposalSha256"], digest)
            self.assertEqual((root/"staged/app/greeting.py").read_text(), GOOD)
            self.assertTrue((root/"staged/.foundation/UNTRUSTED_DO_NOT_EXECUTE").exists())
            with self.assertRaises(ValueError):
                verify_project(root / "staged")

    def test_cli_review_and_stage(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            q, digest = prepare(root)
            self.assertEqual(main(["review", "--quarantine", str(q), "--confirm-sha", digest,
                                   "--decision", "approve", "--dest", str(root / "decision.json")]), 0)
            self.assertEqual(main(["stage", "--quarantine", str(q),
                                   "--approval", str(root / "decision.json"),
                                   "--dest", str(root / "staged")]), 0)

    def test_reject_wrong_or_short_digest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            q, digest = prepare(root)
            for sha in ("abcd", "0"*64):
                with self.assertRaises(ReviewGateError):
                    record_decision(q, sha, "approve", root / "unused")
            self.assertFalse((root / "unused").exists())

    def test_denied_decision_blocks_stage(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            q, digest = prepare(root)
            receipt = record_decision(q, digest, "reject", root / "decision.json")
            with self.assertRaises(ReviewGateError):
                stage_reviewed_proposal(q, receipt, root / "blocked")
            self.assertFalse((root / "blocked").exists())

    def test_tamper_quarantine_after_approval(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            q, digest = prepare(root)
            receipt = record_decision(q, digest, "approve", root / "decision.json")
            proposal = json.loads((q / "proposal.json").read_text())
            proposal["changes"][0]["content"] = BAD
            (q / "proposal.json").write_text(json.dumps(proposal))
            with self.assertRaises(ReviewGateError):
                stage_reviewed_proposal(q, receipt, root / "blocked")
            self.assertFalse((root / "blocked").exists())

    def test_reject_forged_or_expired_decision(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            q, digest = prepare(root)
            receipt = record_decision(q, digest, "approve", root / "decision.json")
            original = json.loads(receipt.read_text())
            for mutation in [
                {"proposalSha256": "a"*64},
                {"authorityDigest": "b"*64},
                {"trustLevel": "cryptographically-authenticated"},
                {"timestamp": (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()},
                {"extra": "execute"},
            ]:
                with self.subTest(mutation=mutation):
                    record = {**original, **mutation}
                    receipt.write_text(json.dumps(record))
                    with self.assertRaises(ReviewGateError):
                        stage_reviewed_proposal(q, receipt, root / "blocked")
                    self.assertFalse((root / "blocked").exists())

    def test_independent_static_oracle_rejects_wrong_and_malicious(self):
        for source in [BAD, MALICIOUS,
                       "def greet(name: str) -> str:\n    return __import__('os').system('id')\n",
                       "def greet(name: str) -> str:\n    return f'Hello, {name}'\n",
                       "def greet(name: str) -> str:\n    return 'Hello, ' + name\nprint('executed')\n"]:
            with self.subTest(source=source):
                self.assertEqual(static_accept_greeting(source)["result"], "fail")

    def test_incorrect_code_cannot_stage(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            q, digest = prepare(root, BAD)
            receipt = record_decision(q, digest, "approve", root / "decision.json")
            with self.assertRaises(ReviewGateError):
                stage_reviewed_proposal(q, receipt, root / "blocked")
            self.assertFalse((root / "blocked").exists())

    def test_cannot_overwrite_existing_project(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            q, digest = prepare(root)
            receipt = record_decision(q, digest, "approve", root / "decision.json")
            dest = root / "existing"
            dest.mkdir()
            (dest / "important").write_text("protected")
            with self.assertRaises(FileExistsError):
                stage_reviewed_proposal(q, receipt, dest)
            self.assertEqual((dest / "important").read_text(), "protected")

    def test_reject_symlink_proposal_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            q, digest = prepare(root)
            target = root / "copy.json"
            target.write_bytes((q / "proposal.json").read_bytes())
            (q / "proposal.json").unlink()
            (q / "proposal.json").symlink_to(target)
            with self.assertRaises(ReviewGateError):
                record_decision(q, digest, "approve", root / "not-created")

    def test_codex_cli_proposal_round_trip_is_static_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            sample=root/"sample"
            init_project("python-service", sample)
            authority=restore_authority(sample)
            task=load_task(DEMO_TASK)
            quarantine=root/"codex-quarantine"
            _write_quarantine(
                quarantine, task, authority, CodexMetadata("codex-cli", "test-model"),
                Proposal("Codex example", (Change("app/greeting.py", GOOD),))
            )
            proposal,digest=read_quarantine(quarantine)
            self.assertEqual(proposal["provider"], "codex-cli")
            approval=record_decision(quarantine, digest, "approve", root/"approval.json")
            evidence=stage_reviewed_proposal(quarantine, approval, root/"staged")
            result=json.loads(evidence.read_text(encoding="utf-8"))
            self.assertFalse(result["executed"])
            with self.assertRaises(ValueError):
                verify_project(root/"staged")

    def test_unknown_proposal_provider_denied(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            quarantine,_=prepare(root)
            path=quarantine/"proposal.json"
            obj=json.loads(path.read_text(encoding="utf-8"))
            obj["provider"]="malicious-adapter"
            path.write_text(json.dumps(obj), encoding="utf-8")
            with self.assertRaises(ReviewGateError):
                read_quarantine(quarantine)

    def test_no_verified_human_identity_claim(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            q, digest = prepare(root)
            record = record_decision(q, digest, "approve", root / "decision.json")
            self.assertEqual(json.loads(record.read_text())["trustLevel"],
                             "local-unattested-no-authentication")

if __name__ == "__main__":
    unittest.main()
