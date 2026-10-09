# Current authority

- Date: 2026-10-09
- Product target: **MVP-2 Multi-Stack Engineering Platform**
- G0 PR #1: Draft, NOT CLOSED
- G1 PR #2: Draft, offline fixture Harness, NOT CLOSED
- G1.1 PR #3: Draft, provider/sandbox policy, NOT CLOSED
- G1.2 PR #4: Draft, real Docker fixture checks, CI green, NOT CLOSED
- G1.3 PR #5: Draft, proposal-only Responses model gateway, NOT CLOSED
- Working branch: \`feat/g13-model-proposal-gateway\` stacked on \`feat/g12-offline-docker-executor\`
- Refresh live GitHub refs, PRs, reviews and exact-head checks before further work.

## Authority (read only what's relevant)
- docs/platform.md
- docs/mvp2-plan.md
- docs/security.md
- docs/contracts.md
- docs/g1-agent-harness.md
- docs/g11-execution-boundary.md
- docs/g12-runtime.md
- docs/g13-model-proposal.md

## Current work
- Independently review G0–G1.3 exact-head tests and security limitations.
- Validate G1.3 schema and negative tests with no paid live inference.
- Plan guarded patch approval + separate sandbox evaluation; do not execute unknown model code in existing G1.2 trusted-fixture runner.
- Do not merge stacked PRs without acceptance.

## Explicitly NOT complete
- No verified real provider API call in CI and no Codex CLI/Claude Code runner.
- No AI-generated code executed, sandboxed or accepted as correct.
- No externally attested proof, production authorization, pilot project adoption or closed gates.
