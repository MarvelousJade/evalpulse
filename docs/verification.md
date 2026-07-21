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

