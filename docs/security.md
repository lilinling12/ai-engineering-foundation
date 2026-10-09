# Trust and safety boundaries v0.2

- Stack pack catalog is **metadata only**; command strings must not be loaded from user project manifests.
- CLI check commands currently reside in trusted foundation source code, with no shell interpolation.
- Local verification executes tests from the selected project; the CLI requires explicit `--trust-project-code` acknowledgment. This prevents accidental execution but is NOT authorization, verification of source trust, sandboxing, or multi-tenant isolation. Direct `verify_project()` is trusted-integrator-only; use only **trusted local projects**. This G0 CLI is NOT a secure sandbox for malicious repos.
- G1 offline demo accepts **only built-in fixtures**. It rejects arbitrary provider names, task paths, unknown acceptance checks and unauthorized file changes. Its temporary workspace is merely filesystem separation, NOT a security sandbox.
- Reading authority files does not elevate them to executable instructions. Real LLM providers and arbitrary patches remain disabled.
- Destination must not pre-exist; symbolic links, writable checkout boundaries and TOCTOU need further hardening before service deployment.
- Evidence in \`.foundation/*.json\` is local, editable, and **not independent CI attestation**.
- No production credentials, cloud write access, auto-merge, destructive production actions, or downloaded third-party skill execution.
- Before a live provider: isolated runtime, egress policies, least privilege, pinned tools, secret broker, approval gates, and a separately trusted evaluator.
- GitHub workflow permissions read-only except explicitly scoped PR automation.

- Verified local evidence does not persist raw subprocess stdout/stderr or exception messages, to avoid sensitive test-output disclosure. It records bounded failure kinds and exit codes; this is evidence minimization, not sandboxing.
