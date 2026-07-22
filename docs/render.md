# Render deployment

The root `render.yaml` is a Render Blueprint for the first-release architecture:

- `evalpulse-web`: public Next.js service.
- `evalpulse-api`: public FastAPI service, migration owner, and Celery worker host.
- `evalpulse-db`: managed PostgreSQL system of record.
- `evalpulse-queue`: private Redis-compatible queue and transient progress store.

## Deploy

1. Push this repository to GitHub or GitLab.
2. In the Render Dashboard, choose **New → Blueprint** and connect the repository.
3. Review the four free resources from `render.yaml` and apply the Blueprint.
4. Wait for the API pre-deploy migration and both service deploys to finish.
5. Open the `evalpulse-web` URL and sign in with `demo@evalpulse.local` / `evalpulse-demo`.
6. Run `python scripts/smoke.py https://<evalpulse-api-host>` to verify the deployed API and worker.

Auto-deploy waits for repository checks to pass. Database and queue URLs are injected from managed resources, while Render generates the session secret. No credentials are committed.

## Cost and limitations

All four resources use free instances for this portfolio deployment. To avoid a paid background-worker instance, the API container also starts a single Celery worker. The web proxy reaches the API through its public Render URL because free web services cannot receive private-network traffic.

Free PostgreSQL expires after 30 days and has no backups. Upgrade it before storing durable data. Free Key Value is intentionally non-persistent; completed runs remain in PostgreSQL, but active jobs can be interrupted by a queue restart. Free web services can cold-start after inactivity, and API and worker capacity are shared.

For a longer-lived deployment, first upgrade PostgreSQL and Key Value, then restore the dedicated worker service from `services/worker/Dockerfile`.
