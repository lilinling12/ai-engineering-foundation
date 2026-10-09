# Current authority

- Date: 2026-10-09
- Product target: **MVP-2 Multi-Stack Engineering Platform**
- G0 on PR #1: Draft, checks previously green, NOT CLOSED
- G1 on PR #2: Draft, fixture-only Harness, NOT CLOSED
- G1.1: Provider contract + offline sandbox command policy on PR #3, NOT CLOSED
- Branch: feat/g11-sandbox-provider-boundary (stacked on feat/g1-agent-harness-protocol)
- Main baseline at preparation: 838c875f0e6912612fee6f5aaa0a723549d47857; refresh live refs

## Authority
- docs/platform.md
- docs/mvp2-plan.md
- docs/security.md
- docs/g1-agent-harness.md
- docs/g11-execution-boundary.md
- docs/contracts.md

## Active task
- Independently review G0/G1 changes and unresolved packaging/security boundaries.
- Verify G1.1 exact-head CI; review sandbox policy and provider request interface.
- Implement actual separately isolated executor, live Codex/Claude adapter, kill-on-timeout and independently verifiable evidence in a later authorized PR.

## Explicitly NOT complete
No real model calls, no sandbox container runs, no hostile code security guarantees, no production tokens or real pilot product adoption. No gate closure or auto-merge.
