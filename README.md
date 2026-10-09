# AI Engineering Foundation

**Product target: MVP-2 Multi-Stack Engineering Platform** (not yet achieved).

An AI-native engineering foundation that shares governance, task handoff, verification, and agent harness contracts across **independent repositories and heterogeneous application stacks**. It does **not** centralize product domains or production data.

## Working vertical slice (proposed)

Requires Python 3.12+. The foundation CLI itself uses Python standard library only.

```bash
python -m foundation catalog
python -m foundation init --stack python-service --dest /tmp/foundation-python-demo
python -m foundation verify --project /tmp/foundation-python-demo

python -m foundation init --stack typescript-api --dest /tmp/foundation-ts-demo
# Requires Node.js and npm; install dependencies inside trusted generated project first:
cd /tmp/foundation-ts-demo && npm install && cd -
python -m foundation verify --project /tmp/foundation-ts-demo
```

Two runnable golden paths are proposed; Java Spring and WeChat packs exist as **contract-only** candidates. No AI agent is launched, no production connection or remote repo is modified, and no claim of production readiness is made.

- [Current authority](docs/handoff/CURRENT.md)
- [Platform vision and boundaries](docs/platform.md)
- [MVP-2 slices and acceptance](docs/mvp2-plan.md)
- [Trust model](docs/security.md)

## Non-negotiables
- Stack-agnostic, agent-agnostic, evidence-driven; per-product business ownership.
- Strict distinction between metadata and executable adapters.
- Independent CI evidence before considering a slice complete.
- Human approval for destructive or production-sensitive actions.

