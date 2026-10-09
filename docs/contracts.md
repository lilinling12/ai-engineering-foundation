# Contracts v0.1

## Stack Pack (catalog)

Each pack has `id`, `ecosystem`, `status` (`runnable` or `contract-only`), `capabilities`, `toolchain` and descriptive boundaries. No commands accepted as data from a project.

## Project manifest

The `.foundation/project.json` manifest records `contract`=`foundation.project/v0`, `stack`, and scaffold version. Only IDs registered in the foundation may be verified. Unknown fields, unsupported contract versions and unsupported scaffoldVersion values are rejected before any check executes. G0 supports scaffoldVersion `0.1.0` only. A `.foundation/UNTRUSTED_DO_NOT_EXECUTE` marker blocks trusted-local verification but is a misuse-prevention guard, **not** a security sandbox.

## Verification evidence

The CLI writes `.foundation/evidence.json`: `contract`, `stack`, `result`, `checks`, `timestamp`, optional `gitHead`, and `trustLevel=local-unattested`. This file is local diagnostics. A future CI proof must bind exact commit SHA, workflow identity, check versions and artifact digest.

## Agent Harness target protocol

`TaskRequest -> AuthoritySnapshot -> Plan -> IsolatedRun -> CheckResults -> IndependentEvaluation -> Handoff`.

This is a proposed protocol, **not an implemented Agent runtime**. Provider adapters must be replaceable and must not authorize themselves for irreversible actions.

