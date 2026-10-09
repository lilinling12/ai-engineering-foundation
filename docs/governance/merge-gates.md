# Engineering merge governance v0.1

Status: **POLICY PROPOSAL**. This file does not configure GitHub repository settings.

## PR gate and human authority

- The working unit is one independent task/Gate, in a PR referencing normative Authority.
- Keep PRs Draft while the implementer is still fixing known blockers. Convert to Ready
  only to request independent review, not to claim a Gate is closed.
- A coding agent may author code, CI and evidence. It MUST NOT approve or merge its own
  change, dismiss blocking reviews, or silently change main/ruleset protections.
- For G0: require Python and TypeScript golden-path CI on exact reviewed head and
  independent human review before merge.
- For G1.2+: also require `offline-docker-smoke`, while keeping its trusted-fixture
  limitation explicit. A green fixture smoke is not a general sandbox assessment.
- Reviewers must examine diff, security boundaries, negative tests, migration/backward
  compatibility, authority, evidence claims, and task completion criteria.
- If the source changes after approval, require current-head CI and review of the
  updated diff. Never reuse old check results as evidence for new head SHA.
- Merge in dependency order PR #1 → #2 → #3 → #4 → #5 → #6, adjusting stacked bases
  and reviewing mergeability after each step. This is a proposal, not an auto-merge order.

## Required GitHub settings (manual administrator configuration)

At `Repository Settings > Rules > Rulesets`, create an active branch ruleset
targeting `main`:

1. Require pull requests before merging.
2. Require **at least 1 approval from a genuine independent reviewer**; prevent
   bypass and require approval of latest push where available.
3. Require status checks `python-platform-tests` and
   `typescript-golden-path`; ensure exact job names are taken from green
   completed GitHub runs and branch protection does not falsely accept a
   similarly named third-party check.
4. Block force push and deletion on main; optionally require conversation resolution.
5. Consider code-owner review, signed commits and linear history when supported
   and aligned with the team workflow.

A separate rule should enforce `offline-docker-smoke` for G1.2+ branches/PRs
where that job exists; do not require it for PR #1 (which has no Docker job).
GitHub required status checks on main must be chosen carefully: a check
required globally cannot be absent from the G0 workflow.

**Critical:** Rulesets are repository settings, not a markdown file.
Verify active enforcement through GitHub's Rules UI/API and an actual blocked
unapproved merge; never represent this policy document as enforcement.

## Verified at 2026-10-09, before change

- Main branch API returned `protected: false`.
- Repository rulesets API returned `[]`.
- Branch Protection endpoint returned 403 `Resource not accessible by integration`.
- Connector tool inventory does not expose a ruleset/branch-protection mutation.
- All six PRs were Draft; PR #1 had no submitted reviews.

Until a repository administrator enables an enforceable ruleset, all merges
must remain manually withheld by policy even if GitHub UI permits them.
