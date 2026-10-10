# G1.4: proposal digest confirmation, local staging, independent static oracle

Status: **PROPOSED**, stacked Draft PR; NOT a closed gate and NOT a production Agent runtime.

## Why stage code without running it?

G1.3 can call a real model and quarantine output, but the current G1.2 Docker smoke
only runs *trusted, fixed, repository-owned fixtures*. It does not establish
safe execution of arbitrary AI-generated code. Do not mix those security domains.

## New local sequence

1. \`foundation propose --model ... --dest QUARANTINE --permit-network\` is optional
   and requires an operator-provided credential. No real API call is performed in CI.
2. Inspect \`QUARANTINE/proposal.json\` manually. Read the proposed source as untrusted text.
3. Copy the \`proposalSha256\` from \`QUARANTINE/evidence.json\`, independently compare
   if necessary, then run:
   \`\`\`bash
   python -m foundation review --quarantine QUARANTINE \
     --confirm-sha FULL_64_CHAR_PROPOSAL_DIGEST --decision approve \
     --dest ./local-decision.json
   python -m foundation stage --quarantine QUARANTINE \
     --approval ./local-decision.json --dest ./new-staged-project
   \`\`\`
4. Staging verifies original evidence hash, exact task/authority and decision binding,
   rejects stale decisions, checks one fixed greeting source against an AST-only
   **independent restrictive static oracle**, and writes source into a new scaffold.
5. The staged project has \`.foundation/UNTRUSTED_DO_NOT_EXECUTE\`. Generic CLI verify
   refuses it. No source is imported, evaluated, compiled or executed by this gate.

## Security and product limitations

- A local decision with a typed digest is **not human identity authentication**;
  a local attacker can forge, edit, replay or delete local files. Do not call this a
  production approval signature or a cryptographically attested workflow.
- The AST verifier checks a deliberately narrow pure-expression fixture.
  It intentionally rejects many otherwise valid implementations; its result is
  NOT general correctness or general Python safety proof.
- SHA-256 provides integrity binding for the observed file pair, not provenance.
- The CLI is intended for a trusted single-user workspace; symlink and TOCTOU
  hardening and an authenticated approval service are necessary before multi-user use.
- No real LLM response is used in CI; network requests and usage costs are not tested.
- Never run staged code via Python, \`foundation verify\`, shell or existing
  G1.2 smoke test. A strong isolation and external evaluator gate is needed first.
- Do not modify or adopt real pilot repositories based on these fixture tasks.

## Next required gate

VM-grade or comparably reviewed isolation for arbitrary generated code, trusted
image/lockfile provenance, authenticated time-bounded approval tokens, independent
acceptance tests outside the agent's writable domain, and exact-SHA external evidence
before any integration into real enterprise/SaaS or control systems.

## Codex CLI proposal review interop (2026-10-10)

- The reviewed provider registry now accepts only `openai-responses` and `codex-cli`. Both retain the same fixed synthetic task, SHA-256 binding, explicit local approval and AST-only static acceptance.
- End-to-end tests take a synthetic `codex-cli` proposal through review and staged project generation. This test **does not invoke a real model** and does not import/execute generated source.
- This is not authenticated approval or a general-purpose production coding Agent review process.
