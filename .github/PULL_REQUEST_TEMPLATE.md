# Pull request review template

## Purpose and authority
- [ ] Link the active Gate from `docs/handoff/CURRENT.md`, with the exact business/technical authority
- [ ] State what is changing **and** what remains out of scope
- [ ] Provide the head/base SHAs and explain any stacked PR dependencies

## Independent verification
- [ ] Exact-head required CI checks green; include workflow URLs, not screenshots alone
- [ ] Negative tests for failures, permissions and regressions
- [ ] No runtime execution of unknown AI-generated code in trusted-local or fixture-only runners
- [ ] Evidence accurately labeled local/unattested vs independent CI attestations

## Safety and compatibility
- [ ] Source/test/architecture/security review by someone other than the implementing agent
- [ ] Manifest/API/stack compatibility and upgrade impacts reviewed
- [ ] No production secrets, unrestricted tools or undocumented external network access
- [ ] Supply-chain lockfiles and action SHA pins verified

## Merge decision (human reviewer)
- [ ] GitHub Ruleset/branch protection enforces the policy documented in `docs/governance/merge-gates.md`
- [ ] Independent reviewer APPROVED, not self-approved by the code author or agent
- [ ] Gate-specific acceptance recorded and handoff updated
- [ ] Downstream PR base drift and required exact-head CI re-checked

**No checkmark in this template constitutes review approval or permission to merge.**
