# MVP-2 delivery plan: vertical slices, not sequential platform versions

**G0 — End-to-end thin slice (this PR).** A user can select a stack, initialize an independent repo seed, run an approved local check and receive a structured evidence file. CLI, catalog, Python and TypeScript golden paths, smoke tests and CI. Java and WeChat explicitly contract-only.

**G1 — Agent job end-to-end.** Request -> authority restore -> sandbox -> one agent provider -> allowed tools -> validation -> independent evaluator -> handoff; exact-head PR evidence. Do not grant production access.

**G2 — Multi-stack actual verification.** Java/Spring, WeChat native and Python simulation packs; CI checks that verify real framework behaviors; one adoption exercise per representative pilot without changing existing product authority.

**G3 — Multi-provider + policy.** Codex/Claude Code adapters, resource limits, tool permissions, artifact provenance, cost accounting, deterministic replay where possible, recovery after interruptions.

**G4 — Platform operation.** CLI remains first-class; optional web portal, fleet observability, version governance and controlled rollout only when real pilots justify them.

## G0 acceptance

- Python standard-library CLI runs on fresh machine;
- starter files copied without overwriting targets or accepting unknown stack IDs;
- Python reference tests run successfully;
- TypeScript template builds and tests with pinned project dependencies in a clean CI install;
- failures yield a nonzero exit code and structured local evidence;
- no externally supplied command is executed from a manifest;
- exact-head GitHub Actions evidence and review are required before closing G0.

## Success measures

Independent acceptance rate, regression count, elapsed time, human minutes, token/tool cost, onboarding time and context-restore failures. No percentage improvement should be claimed before baseline measurement.

## MVP-2 is not

A completed product at G0; a giant multi-agent control plane; Kubernetes-first runtime; common domain database; automatic production deployer.

