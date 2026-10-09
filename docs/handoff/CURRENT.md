# Current authority

- Date: 2026-10-09
- Target: **MVP-2 Multi-Stack Engineering Platform**
- G0 PR #1: Draft, NOT CLOSED
- G1 PR #2: Draft, fixture-only Harness, NOT CLOSED
- G1.1 PR #3: Draft, sandbox policy planner, NOT CLOSED
- G1.2 PR #4: proposed **actual offline Docker runner and CI smoke**, NOT CLOSED
- Current branch: `feat/g12-offline-docker-executor` stacked on `feat/g11-sandbox-provider-boundary`
- Refresh GitHub live refs, PRs, reviews and exact-head checks on every session.

## Authority
- docs/platform.md
- docs/mvp2-plan.md
- docs/security.md
- docs/g1-agent-harness.md
- docs/g11-execution-boundary.md
- docs/g12-runtime.md
- docs/contracts.md

## Active work
1. Inspect exact-head G1.2 GitHub hosted smoke results and actual Docker logs.
2. Audit execution runtime, timeout cleanup, Docker daemon assumptions, acceptance separation and injection risks.
3. Do not merge until code review and all blocking Gate criteria are met.
4. Move next to real Codex integration ONLY after independent runtime security review and key isolation.

## Explicitly NOT achieved
- No real Codex/Claude execution or AI-authored code run.
- GitHub-hosted Docker smoke is not proof of hostile multi-tenant security.
- No signed independent attestation, no pilot adoption, no production releases.
- No G0/G1/G1.1/G1.2 Gate closure or merge authorization.
