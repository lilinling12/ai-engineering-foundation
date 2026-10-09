# Platform thesis and architecture v0.2

## Decision

Build directly toward **MVP-2 Multi-Stack Engineering Platform**. MVP-0 governance and MVP-1 harness are capabilities verified **inside MVP-2 vertical slices**, not separately shipped products.

## Why

AI coding output is cheap relative to the cost of proving domain correctness, maintaining authority, isolating execution and catching regressions. Four pilots deliberately span enterprise SaaS, simulation and optimization, WeChat consumer apps, and Agent Evals.

## Five planes

- **Governance**: product authority, ADRs, non-bypassable safety policies, versioned contracts.
- **Stack packs**: declared ecosystem, compatibility, capability mapping, pinned reference implementations.
- **Harness**: restore -> plan -> execute -> verify -> evaluate -> handoff, with multiple coding-agent providers.
- **Verification**: independently executed checks and signed/attested evidence where supported.
- **Recipes**: product-specific composition of stacks and policies, keeping each product's own domain, data and release rights.

## Architecture principles

- Project repositories are autonomous. No central production database and no compulsory shared runtime.
- TypeScript web/API, Java enterprise, Python simulation/evals and native WeChat are all first-class targets.
- Agent provider integration uses an adapter protocol; no product depends on one specific model.
- Agent plans are proposals, not authority. Tool use is sandboxed and subject to approval and policy.
- Hard constraints are checked in tooling/CI. Repository documentation is navigable and concise.
- Verification evidence binds to the code revision and check definitions; local CLI evidence is **not** a CI attestation.

## Pilot contracts

1. HK-RCHE: tenant boundaries, admissions, financial state transitions, audit.
2. Macau Commercial Energy OS: BOPTEST experiment provenance, tariffs, deterministic safety gates, Python optimization.
3. ToC Social Approval: native WeChat runtime, share/approval lifecycle, visual and navigation regression.
4. Agent Verification: repeatable datasets, trace provenance, sandbox isolation, scoring reproducibility.

No changes to pilot repos are authorized by this architecture alone.

