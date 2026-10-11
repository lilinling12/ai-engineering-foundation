# G1.6 — Disposable Offline Evaluation of Synthetic Agent Proposals

**Gate status: experimental / NOT CLOSED.** Product target remains MVP-2.

## Executable slice

\`g16-synthetic-offline-eval\` in GitHub Actions runs with **no API secrets and no model inference**:

1. The code-owned \`fixture-pass\` emits a synthetic proposal *labelled for the Codex adapter*;
   the label is not proof that Codex generated it.
2. The model-proposal quarantine and digest logic validate it.
3. A **synthetic, automated test decision** is used solely for this fixture run;
   it is not a human approval, and may never authorize live code.
4. G1.4's AST-only static acceptance stages the proposal into a separate workspace.
5. G1.6 launches \`python -B -m unittest discover -s /acceptance -v\` inside a network-off
   Docker container. The acceptance suite is a separate read-only mount, not part
   of the proposal's writable workspace.
6. Additional CI-generated wrong-answer and deliberate timeout samples prove that
   acceptance fails wrong code and that the runtime enforces deadlines and confirms
   daemon-side removal. These negative samples bypass G1.4 staging *only as test fixtures*.
7. Emits SHA-bound, image-digest-labelled, **unsigned** JSON evidence with statuses
   and no raw source logs.

The execution controller runs only on opt-in GitHub-hosted CI. It rejects directories
outside its own synthetic temporary run root, check commands are fixed in foundation
source, and no CLI option accepts arbitrary code paths. It never connects to the
G1.2 fixed-fixture executor, never imports candidate source on the host and never
uses \`foundation verify --trust-project-code\` on the candidate.

## Limitations and risks

- Docker is **not** a VM-grade hostile multi-tenant boundary; the daemon is privileged,
  kernel attack surface remains, and environment-variable host checks are not host
  identity attestation. This is only a short-lived GitHub-hosted, **synthetic** CI
  experiment, not permission to run real external AI-authored code.
- The initial Python image pull uses the mutable \`python:3.12-slim\` tag. Its resolved
  digest is used for each later container, but this is not reproducible image pinning.
- The tests do not demonstrate arbitrary developer tasks, multiple Stack Packs,
  live model coding, authenticated approvals, key isolation, signed evidence,
  or business acceptance.
- Fail closed on cleanup uncertainty. Prevent output-based information leakage:
  stdout/stderr are discarded. Artifact contains only fixed classifications.
- Workflow PR authors with write access can modify their branch's workflow;
  **do not add secrets to this workflow**, even after G1.6 moves forward.

## Production runtime exit conditions

1. VM-/microVM-grade workload isolation with externally verified host networking,
   egress proxy, resource limits and complete process-tree termination.
2. Inference credentials isolated from generated-code execution, ephemeral scoped
   access and auditable provider request budget.
3. Independently versioned, immutable validation oracle inaccessible to coding Agent.
4. Authenticated, time-bound patch approval, exact-run signed provenance, audit retention.
5. Real model task with explicitly authorized spend and synthetic-only input,
   independently repeated on a verified segregated host.
6. Then controlled adoption into independent Python/Node/Java/WeChat Stack Packs.

G1.6 and earlier Gates remain subject to independent review and Issue #7.
