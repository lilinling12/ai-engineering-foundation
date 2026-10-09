# Current authority

- Date: 2026-10-09
- Product target: **MVP-2 Multi-Stack Engineering Platform**
- Focus: **integration audit and remediation, not new features**
- All PRs #1–#6 are stacked Draft PRs, **NOT MERGED**, G0–G1.4 **NOT CLOSED**.
- PR #4 corrected fixture allowlisting, Docker cleanup verification and mount argument filtering; exact-head checks green before propagation.
- G1.2 fixes synchronized to PR #5 and #6 via merge commits.
- Working branch: `feat/g14-review-static-acceptance` (PR #6).
- Refresh main, PR heads, checks and review decisions from GitHub each session.

## Read next
1. `docs/integration-audit-2026-10-09.md` — authoritative open risk register and merge gates
2. `docs/mvp2-plan.md`
3. `docs/security.md`
4. Only the active issue's relevant component documentation

## Active task (do not skip)
- Verify PR #5/#6 propagated merge commits and exact-head checks.
- Fix G0 reproducible TypeScript dependency lock and CI action pinning.
- Arrange actual independent review; do NOT self-approve or auto-merge.
- Resolve G0 acceptance before closing G1+.
- Never execute AI-generated code in the current fixture-only Docker runtime.

## Not done
No gate accepted or merged; no authenticated production approval, no
independent untrusted-code sandbox assurance, no real Codex CLI/Claude Code
integration or signed provenance, no pilot-product adoption.

## Integration sync (2026-10-09)

- G0 npm lockfile, `npm ci` golden path, and verified full Action SHAs propagated through all stacked PRs.
- Risk INT-004 and INT-005 implementation remediated; independent reviewer acceptance remains open.
- After propagation, check exact HEAD SHA of every branch and workflows; do not cite previous green results for updated SHAs.
