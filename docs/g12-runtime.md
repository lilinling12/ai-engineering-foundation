# G1.2 — Real offline Docker verifier (CI proof; not production sandbox)

Status: proposed / stacked Draft PR. Product target remains MVP-2.

## What runs

- \`foundation.docker_executor\` launches the Docker process on a **GitHub-hosted ephemeral runner** only if three explicit host flags match.
- The allowed command registry is fixed in foundation source, never read from task/manifest text.
- The interpreter runs as UID 65534, network disabled, dropped capabilities, read-only root and code mount, with resource limits. The default Docker daemon seccomp remains in effect; the host's actual daemon configuration MUST be reviewed.
- \`--name\` gives the controller an addressable container. On deadline, it kills the Docker client and force-removes the named container via daemon API; cleanup failure is a failed check.
- Independent acceptance tests are bound separately from the worktree as read-only files.
- Github-hosted job performs four REAL checks: passing implementation, deliberately failing implementation, no-egress/root-write/nonroot policy assertions, and enforced timeout.
- Emits a local CI artifact including exact GitHub SHA and resolved image digest. The artifact is **not signed or cryptographically attested**.

## Run via GitHub Actions

\`offline-docker-smoke\` in \`.github/workflows/foundation-ci.yml\`. No secrets or external pilot repos are used.

Image resolution: the CI smoke first pulls a publicly tagged Python image, resolves the digest on the runner, and uses \`--pull=never\` from that point forward. This proves digest resolution for the run, **not reproducible supply-chain pinning**, since the initial tag is mutable.

## Never do

- Never run an arbitrary model patch or third-party repository via this smoke command.
- Never execute on a self-hosted runner or workstation by bypassing guards.
- Never mount Docker socket, home directory or cloud keys into an execution container.
- Never report Docker alone as hostile multi-tenant isolation.

## Required before first real Codex/Claude task

1. Separate Agent inference environment from untrusted check runner. Keep inference credentials outside code workspace; use short-lived scoped tokens/egress proxy.
2. Runtime-specific, reviewed image digests and dependency locks, approved allowlisted command catalogs for each Stack Pack.
3. More robust sandbox isolation (VM-grade for untrusted tenants), host escape/DoS threat analysis and approval/audit.
4. Provider lifecycle: authenticated run, cancellation, bounded time/cost, patch review and error state machine.
5. Independent external acceptance against a preserved test oracle, signed or externally verified exact-head execution evidence.

The fact that CI runs real Docker does not make G1.2 or G1 fully accepted.
