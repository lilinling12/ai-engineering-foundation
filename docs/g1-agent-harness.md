# G1 Agent Harness protocol — development preview

Status: **stacked Draft PR / NOT ACCEPTED**.

## Vertical slice included

- A strict versioned TaskRequest with a fixed fixture task/acceptance registry.
- Authority restore and SHA-256 snapshot digest.
- A replaceable AgentProvider protocol.
- Offline built-in fixture providers (correct and deliberately incorrect).
- Pre-apply allowed-path verification and rejection of path escape / partial edits.
- Temporary working tree, stack verification, **independent acceptance assertions**.
- Structured machine-readable local evidence, with explicit trust limits.

This proves the orchestration interfaces and that a faulty proposal can fail independent
acceptance; it **does not** invoke an AI model.

## Local acceptance

\`\`\`bash
python -m foundation agent-demo --provider fixture-pass --dest /tmp/g1-pass
python -m foundation agent-demo --provider fixture-fail --dest /tmp/g1-fail # exits 1
python -m unittest discover -s tests -v
\`\`\`

## Planned production transition

1. Formalize task schema, allowed paths, tool capability policies and approvals.
2. Provide an actual security boundary (isolated container/VM with no host secrets,
   enforced network and resource policies) **before running real provider output**.
3. Integrate one AI coding provider through a versioned adapter with cancellation and trace.
4. Execute independent evaluator against trusted acceptance tests, separately from agent.
5. Add exact-head, externally verifiable run provenance and tamper detection.
6. Create operational pilots with explicit per-repository user approval.

Security: A temporary copy is **not** a sandbox; Python imports execute local code.
Never run real or untrusted model-generated patches in this demo.
