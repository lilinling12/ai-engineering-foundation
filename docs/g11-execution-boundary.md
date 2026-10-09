# G1.1 — Provider execution boundary (design + policy checks)

Status: **PROPOSED** in a Draft PR stacked on G1. No live provider or container execution is claimed.

## Trust zones

A. Orchestrator: validates task/authority snapshot, grants narrowly-scoped capabilities and records approvals. It is not trusted to approve its own generated code.
B. Provider adapter: Codex / Claude Code. Produces a proposed patch from task and authority; no shell privileges or production tokens are granted by default.
C. Offline verifier: checks untrusted code in an isolated workspace with pinned dependencies and no outbound network.
D. Evidence collector: independent runner reports exact commit, check definition and outcome; local JSON is NOT attested CI evidence.

## Current deliverable

- \`foundation/provider_contract.py\`: provider-neutral request and budget schema, no live execution.
- \`foundation/sandbox.py\`: **pure Docker argv planner only** with digest-pinned image, no network, read-only root filesystem, zero added Linux capabilities, no-new-privileges, unprivileged user, memory/CPU/PID limits, readonly workspace, no host secrets.
- Negative tests ensure denial of arbitrary check IDs, non-pinned image tags, network and resource escalation.

## Blocking gaps before real AI tasks

1. Do not treat Docker flags or a temporary directory as proven hostile-code isolation. Assess container escape and host daemon threat; consider stronger VM isolation for multi-tenant agents.
2. Runtime must enforce timeout, cancellation, artifact quotas and kill-on-timeout (the planner does not execute or enforce those).
3. Workspace image must be audited and pinned to its **real** digest, with immutable tools/lockfiles. Never invent digest values from tests.
4. Need separate provisioning/model network from offline untrusted code evaluation. A network-disabled runtime cannot call hosted inference APIs.
5. Need a safe patch-application protocol, symlink/path race protection, read-only acceptance fixtures outside writable workspace and no user-controlled command injection.
6. Trusted evaluator should run out-of-band and attach signed/external exact-head CI evidence.
7. Need real provider integration with scoped auth and explicit approvals for irreversible operations.

## Why

OpenAI documents \`codex exec\` for noninteractive coding with configurable sandbox policies, but those controls do not replace independent host-level isolation. Docker supports read-only roots, capability drop, no-new-privileges and resource limits, which are necessary defense-in-depth but not a sufficient complete isolation guarantee.

## Gate acceptance

Tests must pass on exact head, security review must approve threat model, and a separate live runtime PR must demonstrate enforcement in an isolated disposable environment. Until then, **no real model-generated code execution**.
