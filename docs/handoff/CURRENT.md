# CURRENT — Integration Audit / G0 reviewer handoff
Last observed: 2026-10-10. **This file is a checkpoint, not a live GitHub status API.**

## Product and branch
- Goal: MVP-2 Multi-Stack Engineering Platform (not yet a complete platform).
- This branch: `feat/g14-review-static-acceptance` / PR #6, stacked on PR #5.
- At the last GitHub check, PR #1 was Ready for review; PR #2–#6 were Draft.
- G0 through G1.4 are **NOT CLOSED**, and no PR was merged.
- `main` baseline: `838c875f0e6912612fee6f5aaa0a723549d47857`.
- Branch protection returned `protected=false`, repository Rulesets `[]`;
  Issue #7 remained Open and PR #1 had no submitted review.
- Always check live refs, status, reviews and exact-head checks before making
  claims. This checkpoint may become outdated at any time.

## Read authority in order
1. `docs/integration-audit-2026-10-09.md`: findings, corrected risk register, merge gates
2. `docs/governance/merge-gates.md`: proposed independent reviewer policy
3. `docs/mvp2-plan.md`: MVP-2 vertical slice scope and acceptance
4. `docs/security.md`, `docs/contracts.md`
5. Current affected Gate's own design (`docs/g14-review-static-acceptance.md`,
   `docs/g13-model-proposal.md`, `docs/g12-runtime.md` as needed)

## Latest engineering change
- G0 `foundation verify` requires `--trust-project-code`; not a sandbox.
- G0 verifier refuses untrusted staged marker and invalid scaffold versions.
- G0 verification evidence no longer persists raw subprocess output or exception text.
- Changes propagated through PR #1–#6 with preserved ancestry.
- Latest SHA and CI must be checked on GitHub; do not reuse older green evidence.

## Immediate next tasks
1. Confirm this branch's exact-head Python/TS/Docker CI, and all upstream PR heads.
2. Arrange **genuine independent review** for PR #1 and enable active `main` Ruleset
   via repository administrator (tracked in Issue #7). Do not self-approve or merge.
3. Keep G1 runtime trust domains separated: fixture-only Docker smoke is not
   arbitrary untrusted-code isolation; model proposals remain quarantined.
4. Once G0 is approved and protection verified, human-controlled integration may
   proceed through PR #1 → #6 in dependency order, with repeated head/base checks.

## Explicitly NOT achieved
No closed Gates, production adoption, authenticated human approval, general hostile-code
sandbox, Codex CLI / Claude Code runtime, or independent cryptographic attestations.
