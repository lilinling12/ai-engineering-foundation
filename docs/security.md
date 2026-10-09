# Trust and safety boundaries v0.1

- Stack pack catalog is **metadata only**; command strings must not be loaded from user project manifests.
- CLI check commands currently reside in trusted foundation source code, with no `shell=True`.
- Local verification executes tests from the selected project; therefore use only **trusted local projects**. This G0 CLI is NOT a secure sandbox for malicious repos.
- The destination must not pre-exist, preventing silent overwrites. Symlinks, writable checkout boundaries, and TOCTOU require hardening before multi-user service deployment.
- Local evidence is self-reported, editable and **not independent attestation**.
- No production credentials, cloud write access, auto-merge, unattended destructive operations, or downloaded third-party skill execution.
- Before remote Agent execution: isolated workspaces, egress restrictions, least-privilege credentials, approval gates, pinned tools, artifact provenance, and independent verification.
- GitHub workflow permissions should be read-only except narrowly scoped PR automation.

