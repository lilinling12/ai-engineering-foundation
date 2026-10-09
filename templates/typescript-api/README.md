# TypeScript API seed

Strict TS module golden path (not yet a Fastify production API).

Requires Node 24 and npm 11. Dependencies are pinned by the committed npm v3
lockfile generated from npm Registry on a clean GitHub-hosted Node 24 runner,
including upstream tarball SHA-512 integrity metadata.

```bash
npm ci --ignore-scripts --no-audit --no-fund
npm run typecheck
npm test
npm run build
```

Do not replace `npm ci` with `npm install` in reproducibility checks, regenerate
the lockfile without a reviewed dependency-upgrade PR, or assume this seed is a
production-ready API. Authentication, API contracts, databases, migration checks
and deployment hardening are explicitly out of scope for G0.
