# G0 dependency & CI reproducibility evidence — 2026-10-09

## Reproducible dependency lock

The TypeScript seed previously had exact top-level dev dependency versions but
**no transitive lockfile**. The GitHub-hosted Node 24/npm 11 workflow bootstrap
generated `package-lock.json` with lockfileVersion 3, resolving exactly
`typescript@5.9.3`, `@types/node@24.0.0` and `undici-types@7.8.0`,
including npm Registry URLs and SHA-512 tarball integrity strings.

Source: GitHub Actions job ID `113787693788`, output delimited with
`FOUNDATION_LOCKFILE_BEGIN/END`. Temporary bootstrap generation code was
removed from the final workflow. Never derive or guess integrity metadata.

## CI acceptance

- Pinned action versions: `actions/checkout` at `11d5960a326750d5838078e36cf38b85af677262`,
  `actions/setup-node` at `49933ea5288caeca8642d1e84afbd3f7d6820020`,
  `actions/setup-python` at `a26af69be951a213d495a4c3e4e4022e16d87065`.
  These were verified against the public GitHub tag refs at audit time.
- Workflow now uses `npm ci --ignore-scripts --no-audit --no-fund` rather than
  `npm install` for the TypeScript template and generated starter.
- Checkout sets `persist-credentials: false`; workflow token `contents: read`.
- Static tests validate lock/manifest consistency and immutable action refs.
- Exact-head GitHub-hosted runs are the acceptance evidence; must verify SHA,
  success results and logs separately. Passing is not code review.

## Remaining risks

Actions and npm package upstream versions may require a controlled upgrade.
The TypeScript template is not yet a real API implementation.
GitHub Branch Protection/Rulesets and independent human review are still needed;
this PR must remain Draft until explicitly accepted.
