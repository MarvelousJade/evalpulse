# Render deployment

The root `render.yaml` is a Render Blueprint for the first-release architecture:

- `evalpulse-web`: public Next.js service.
- `evalpulse-api`: public FastAPI service and migration owner.
- `evalpulse-worker`: private Celery background worker with the durable redispatch loop.
- `evalpulse-db`: managed PostgreSQL system of record.
- `evalpulse-queue`: private Redis-compatible queue and transient progress store.

## Deploy

1. Push this repository to GitHub or GitLab.
2. In the Render Dashboard, choose **New → Blueprint** and connect the repository.
3. Review the five resources from `render.yaml`, approve the estimated cost, and apply the Blueprint.
4. Wait for the API pre-deploy migration and all three service deploys to finish.
5. Open the `evalpulse-web` URL and sign in with `demo@evalpulse.local` / `evalpulse-demo`.
6. Run `python scripts/smoke.py https://<evalpulse-api-host>` to verify the deployed API and worker.

Auto-deploy waits for repository checks to pass. Database and queue URLs are injected from managed resources, while Render generates the session secret. No credentials are committed.

## Cost and limitations

The API and Celery worker use Starter instances because background workers have no free tier and a free API cannot receive private traffic from the web service. The web service, database, and queue use free instances for a portfolio deployment.

Free PostgreSQL expires after 30 days and has no backups. Upgrade it before storing durable data. Free Key Value is intentionally non-persistent; completed runs remain in PostgreSQL, but active jobs can be interrupted by a queue restart. Free web services can cold-start after inactivity.

For a longer-lived deployment, first upgrade PostgreSQL, then Key Value. No code or Blueprint topology change is required.
