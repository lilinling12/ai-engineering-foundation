# Engineering Integration Audit — 2026-10-09

Status: **BLOCKING REVIEW IN PROGRESS**. Target: MVP-2 Multi-Stack Engineering Platform.
Scope: stacked PRs #1–#6. Evidence: live GitHub branch/PR state, exact-head CI checks,
review conversations and source inspection. This document is **not an approval**.

## Live baseline at review

- main: `838c875f0e6912612fee6f5aaa0a723549d47857` (not protected at initial review).
- PR #1 G0, #2 G1, #3 G1.1, #4 G1.2, #5 G1.3, #6 G1.4: all OPEN/DRAFT, none merged.
- Prior to remediation: all six exact-head workflows green; **zero PR review comments**
  and **no documented acceptance decisions**.
- PR #4 remediation `ac4f3547ec0317eaa021182a9d6109fe0e618c31`
  passed Python, TypeScript and Docker checks, repeated through push/PR workflows.
- Remediation propagated to PR #5 and #6 as merge commits preserving branch ancestry.
  Refresh each exact-head status after propagation; old green checks do not cover new SHAs.

## Findings (risk / origin / disposition)

| ID | Severity | Finding | Disposition / exit evidence |
| --- | --- | --- | --- |
| INT-001 | High | G1.2 Docker executor would accept arbitrary workspace paths even though documentation claimed reviewed fixtures only | **FIXED in PR #4**: strict in-repo fixture/acceptance identity; negative tests |
| INT-002 | High | Docker cleanup ignored nonzero `rm -f` exit code | **FIXED in PR #4**: verify absence using inspect; fail closed if container still exists or daemon cannot confirm; tests |
| INT-003 | Medium | Docker `--mount` source path was embedded into a comma-delimited argument without delimiter filtering | **FIXED in PR #4**: reject comma/control characters; negative tests |
| INT-004 | High / G0 exit blocker | TypeScript template has no committed `package-lock.json`; CI uses mutable `npm install`, not `npm ci` | **OPEN**: generate/review audited lockfile, use clean frozen install, run full exact-head checks |
| INT-005 | Medium / supply chain | GitHub Actions use mutable `@v4/@v5` tags instead of verified full commit SHA | **OPEN**: pin verified action SHAs or enforce an approved workflow lock policy; no unverified hashes |
| INT-006 | High / production adoption | G1.4 local SHA confirmation is not authenticated human approval; local files and evidence can be forged | **OPEN BY DESIGN**: never enable production adoption until authenticated approval/audit service |
| INT-007 | High / live AI execution | G1.2 tests only fixed fixtures; no stronger reviewed isolation, no credible arbitrary model-code runtime | **OPEN BY DESIGN**: no real generated-code execution; review isolation and independent tests first |
| INT-008 | Medium / evidence | Local evidence JSON and CI artifact are not cryptographic provenance or signed acceptance | **OPEN BY DESIGN**: exact-SHA verified attestation and trust chain required |
| INT-009 | Medium / integration | Six stacked Draft PRs with no review/acceptance evidence; main unprotected at initial review | **OPEN**: owner review and protected branch/required CI policy before merges |

## Scope and quality interpretation

- G0 proves small Python/TypeScript seeds, not full production templates.
- G1 runs **only** in-repo fixture providers; its local Python test execution is not
  suitable for arbitrary generated source.
- G1.1 defines static sandbox/provider policies, not a real coding runtime.
- G1.2 executes containerized **fixed tests**; Docker on ephemeral CI does not imply
  a hardened hostile tenant/VM boundary. Environment flags are not authentication.
- G1.3 supports optional OpenAI Responses **proposal-only** inference. CI tests
  simulated transports, not paid real requests, Codex CLI or Claude Code.
- G1.4 checks a fixed Python AST expression, applies only to a disposable new
  workspace and marks it untrusted; removing a marker is not a security boundary.
  The local decision record cannot prove operator identity.

## Action order (no auto-merge)

1. **G0**: resolve INT-004/005, require exact-head tests and independent review.
2. Review/accept **PR #1** only; if approved, merge by a human owner, never by this agent.
3. Verify no base drift; then review PR #2 → #3 → #4 → #5 → #6 in order,
   retargeting each base as needed. Keep proofs bound to updated exact head.
4. Before pilot adoption, close INT-006/007/008/009 with their own verifiable gates.
5. Do not create a seventh stacked feature branch to avoid addressing blockers.

## Acceptance rules

A passing CI result is necessary, not sufficient. Each gate requires actual source
review, required automated tests, explicit owner acceptance, and a recorded decision.
No gates are closed by this audit alone.
