# G1.3 Model Proposal Gateway — first live inference integration

Status: stacked Draft PR; **NOT CLOSED**. Main MVP-2 objective remains unchanged.

## Deliberate decision

Separate **model inference** from **code execution**. Live inference uses OpenAI Responses
with Structured Outputs; model receives a narrowly bounded built-in fixture task and
an authority excerpt. It gets **zero function/shell tools**. The response is treated as
untrusted data, checked against allowed paths and size limits, then written into a
**quarantine directory**. It is neither applied nor executed.

The adapter can make a real HTTPS request when a maintainer explicitly opts in, provides
a valid model identifier and uses their own API credential. No paid live call is run in CI.
This is an OpenAI Responses proposal adapter, NOT Codex CLI and not a full coding Agent.

## Commands (on a personally controlled trusted environment)

\`\`\`bash
# Pass credentials via your own secret manager or environment, never commit them.
export OPENAI_API_KEY=...   # illustrative only; do not paste secrets into PRs/logs
python -m foundation propose \
  --model YOUR_AVAILABLE_MODEL_ID \
  --dest /tmp/g13-proposal \
  --permit-network
\`\`\`

Outputs: proposal.json and evidence.json; result **pending-review** and executed=false.
No verification of proposed code is implied. Review proposal.json manually.

## Design limitations

- The only accepted live task is the fixed python greeting fixture. This is intentional;
  arbitrary projects, customer data, repository files and custom prompts are out of scope.
- CLI is an opt-in developer tool, not a secure production credential boundary; local
  environment variables can leak to other same-user processes or diagnostics.
- Model API output is not attested, may be wrong or malicious, and is never automatically applied.
- No claim that the provider was exercised against the real API until a separately recorded
  authorized live run with redacted evidence.
- SDK/CLI runtime adapters for Codex / Claude Code require their own independent security review.
- Future workflow: quarantined proposal -> approval -> detached write-only patch workspace ->
  isolated verifier -> independent oracle -> exact-SHA CI proof -> handoff.

## Evidence requirements

Require response ID/model metadata only after a real authorized run, with secrets and private
source redacted. Model usage and cost must be measured later. Local evidence is not a
cryptographic or GitHub CI attestation.

## References

OpenAI Responses API Structured Outputs and non-interactive Codex exec documentation.

## Credential-safe HTTPS transport (2026-10-10)

- Model proposal requests now use the **fixed** `https://api.openai.com/v1/responses` endpoint, a standard certificate-validating HTTPS handler, and an opener that **does not follow HTTP redirects**.
- The request ignores ambient `HTTP_PROXY`/`HTTPS_PROXY` settings via an empty explicit proxy handler. This is intentional fail-closed behavior and may require an approved future proxy integration for enterprise networks.
- An HTTP 30x response is treated as an error; the API key must not be forwarded to redirect targets. The final effective response URL must equal the approved API URL.
- Tests verify redirect rejection, empty proxy configuration, one-request behavior, redacted redirect errors and destination mismatch.
- This is application-layer outbound request hardening, **not host egress filtering**, API key escrow, secure coding-agent sandboxing or evidence attestation. No paid model request was made to verify this change.

## Actual Codex CLI interface compatibility (2026-10-10)

- `foundation/codex_cli_adapter.py` now constructs a **versioned, strict proposal-only** `codex exec` invocation for the reviewed Python greeting fixture.
- It uses `read-only`, ephemeral sessions, ignored user config and a bounded schema response. It never executes the planned command; output parsing reuses the existing source-path allowlist.
- `codex-cli-interface-smoke` installs the exact `@openai/codex@0.162.1` binary into an ephemeral, credentialless GitHub job and tests CLI availability/flags. **No live inference, sandbox code execution or API charges** occur in CI.
- The CI-only Codex CLI dependency lockfile is now committed from the npm 11 GitHub-hosted runner, including upstream SHA-512 integrity fields for the Codex executable and platform variants. It uses `npm ci`; verified dependency integrity alone is **not** production provenance or a security sandbox.
- A future isolated runtime must enforce image provenance, outbound inference endpoint filtering, tool-level allowlists, audited credentials and separate evaluation before invoking the CLI with real credentials. Codex flags alone are NOT trusted host isolation.
