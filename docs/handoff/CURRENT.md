# Current authority

- Date: 2026-10-09
- Product target: **MVP-2 Multi-Stack Engineering Platform**
- Base Gate: **G0 / Thin Vertical Slice** on PR #1 — checks passing, Draft, **NOT CLOSED**
- Stacked preview: **G1 / Agent Harness Contract & Offline Golden Path** on PR #2 — **NOT CLOSED**
- Work branch: \`feat/g1-agent-harness-protocol\`, base \`feat/mvp2-platform-vertical-slice\`
- Main SHA at initial handoff: \`838c875f0e6912612fee6f5aaa0a723549d47857\`; refresh live GitHub state

## Read
- docs/platform.md
- docs/mvp2-plan.md
- docs/contracts.md
- docs/security.md
- docs/g1-agent-harness.md

## Current work
1. Resolve G0 peer review, dependency lockfile and trusted-local boundaries.
2. Independently review G1 policy/acceptance and check its exact-head CI.
3. Plan actual sandbox boundary and AI provider adapter; do not execute untrusted generated code until implemented.

## Explicitly not achieved
- No live coding LLM in this G1 preview. Only deterministic built-in fixture providers.
- No secure sandbox; temporary workspace isolation is NOT threat isolation.
- No adoption of pilot application repositories.
- No production or external repository access.
- No G0 or G1 closure or merge authorization.
