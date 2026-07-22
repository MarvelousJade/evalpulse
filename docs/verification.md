# Verification

Run the checks from the repository root:

```shell
ruff check .
mypy python/evalpulse
pytest --cov=evalpulse
npm run lint
npm run typecheck
npm test
npm run build
docker compose config --quiet
kubectl kustomize infra/k8s/overlays/kind
```

Measured counts and performance claims belong here only after the commands have run in a clean environment. The local Kubernetes overlay is a demonstration path and is not described as production infrastructure.

## Verified baseline

Verified locally on July 21, 2026 with Python 3.12.10, Node 24.11.0, Docker 29.6.1, and kubectl/Kustomize 1.36.1:

- 7 Python unit/integration tests passed with 81% statement coverage.
- 2 typed API-client contract tests passed.
- 1 Playwright browser workflow passed against the Compose stack.
- Ruff, strict mypy, ESLint, TypeScript, and the optimized Next.js build passed.
- `npm audit --audit-level=moderate` reported zero known vulnerabilities.
- All four application images built and ran as non-root with read-only root filesystems.
- The HTTP smoke script completed two Celery runs and confirmed the expected failed regression decision against PostgreSQL and Redis.
- The `kind` and production Kustomize overlays rendered successfully. A local cluster run was not recorded because `kind` was not installed; CI owns that deployment proof.
