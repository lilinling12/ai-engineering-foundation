# Current authority

- Date: 2026-10-09
- Product target: **MVP-2 Multi-Stack Engineering Platform**
- G0 PR #1: Draft, NOT CLOSED
- G1 PR #2: Draft, fixture-only Harness, NOT CLOSED
- G1.1 PR #3: Draft, sandbox policy, NOT CLOSED
- G1.2 PR #4: Draft, CI Docker checks of trusted fixtures, NOT CLOSED
- G1.3 PR #5: Draft, model proposal quarantine (optional real API), NOT CLOSED
- G1.4 PR #6: Draft, local digest review + static staging, NOT CLOSED
- Work branch: `feat/g14-review-static-acceptance` stacked on `feat/g13-model-proposal-gateway`
- Re-check live GitHub refs, reviews and exact-head CI on each session.

## Read only relevant current authority
- docs/platform.md
- docs/mvp2-plan.md
- docs/security.md
- docs/contracts.md
- docs/g12-runtime.md
- docs/g13-model-proposal.md
- docs/g14-review-static-acceptance.md

## Active work / blockers
- Review stacked PRs #1–#6 and verify G1.4 exact-head CI.
- Do not merge until explicit gate review and integration acceptance.
- Implement authenticated approvals and strong isolated execution before
  running arbitrary model-generated source or extending beyond greeting fixture.
- Determine how to reduce stacked PR depth by reviewing and merging sequentially.

## Not achieved
- No verified paid model call in CI, no Codex CLI/Claude Code Agent runtime.
- No execution of AI-authored code, no proven multi-tenant sandbox.
- No signed approval, external attestation, real pilot adoption or closed Gate.
