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
