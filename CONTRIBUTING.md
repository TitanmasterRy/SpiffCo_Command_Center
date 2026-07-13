# Contributing to SpiffCo Command Center

Thanks for your interest in contributing! This document explains how to get set up
and what we expect from contributions.

## Getting started

1. Fork and clone the repository.
2. Follow the Quick start in [README.md](README.md) to run backend and frontend.
3. Read [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) and
   [docs/CODING_STANDARDS.md](docs/CODING_STANDARDS.md).

## Workflow

1. Open (or find) an issue describing the change before starting large work.
2. Create a feature branch from `main`: `feat/<short-name>` or `fix/<short-name>`.
3. Keep pull requests focused — one logical change per PR.
4. Make sure the project builds and all tests pass:
   - Backend: `cd backend && pytest`
   - Frontend: `cd frontend && npm run build && npm test`
5. Update documentation and `CHANGELOG.md` when behavior changes.

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(power): add battery drain forecast
fix(frm): reconnect after game session restart
docs: clarify docker deployment
```

## Code requirements

- Every public function/class has a docstring (backend) or TSDoc comment (frontend).
- New behavior ships with unit tests.
- No duplicated logic — extract shared helpers.
- Strong typing everywhere: no `Any`/`any` without a justifying comment.

## Reporting bugs

Include: OS, game version, FRM mod version, app version, backend logs
(`backend/logs/`), and reproduction steps.

## Code of conduct

Be kind. Assume good intent. Keep discussions technical.
