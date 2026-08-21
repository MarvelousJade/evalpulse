# Render + Neon deployment

The root `render.yaml` deploys the application on Render and uses Neon for durable PostgreSQL:

- `evalpulse-web`: public Next.js service.
- `evalpulse-api`: public FastAPI service, migration owner, and Celery worker host.
- Neon PostgreSQL: external system of record.
- `evalpulse-queue`: private Redis-compatible queue and transient progress store.

`DATABASE_URL` and `MIGRATION_DATABASE_URL` are secret values entered in the Render Dashboard. They
must never be committed. The application uses Neon's pooled URL, while Alembic uses the direct URL
because schema migrations are not supported reliably through transaction-mode poolers.

## Fresh deployment

1. Create a Neon project using PostgreSQL 17 in a region close to Render's Ohio services.
2. Create an `evalpulse` database.
3. In Neon's **Connect** dialog, copy both connection strings:
   - pooling enabled: use as `DATABASE_URL`;
   - pooling disabled: use as `MIGRATION_DATABASE_URL`.
4. In the Render Dashboard, choose **New → Blueprint**, connect this repository, and apply
   `render.yaml`.
5. Enter the two Neon URLs when Render prompts for the unsynced environment variables.
6. Wait for the API startup migration and both service deploys to finish.
7. Open `evalpulse-web` and sign in with `demo@evalpulse.local` / `evalpulse-demo`.
8. Run `python scripts/smoke.py https://<evalpulse-api-host>`.

Both Neon URLs must retain the generated TLS query parameters. Plain `postgresql://` URLs are
accepted; application configuration selects psycopg automatically. On an empty Neon database, the API
startup applies all Alembic migrations before serving traffic.

## Migrate the existing Render database

> A suspended Render database cannot be exported. To retain its data, upgrade `evalpulse-db` within
> Render's 14-day retention window to restore access, then migrate it. If the stored data is
> disposable, skip the export and restore: point Render at an empty Neon database and let Alembic
> initialize it.

Use PostgreSQL 17 client tools and a new, empty Neon database. Do not deploy the API against that
Neon database before restoring the dump.

1. Temporarily upgrade `evalpulse-db` and confirm its **External Database URL** works.
2. Create the Neon project and `evalpulse` database described above, then copy its **direct**
   connection string (pooling disabled).
3. Stop the Render API during the final dump so the API and colocated worker cannot write to the
   source.
4. Keep both URLs in shell environment variables rather than repository files. In PowerShell:

   ```powershell
   $env:RENDER_DATABASE_URL = Read-Host "Render External Database URL"
   $env:NEON_MIGRATION_DATABASE_URL = Read-Host "Neon direct database URL"

   pg_dump -Fc -v -d "$env:RENDER_DATABASE_URL" --schema=public -f render_dump.bak
   pg_restore -v -d "$env:NEON_MIGRATION_DATABASE_URL" `
     --no-owner --no-acl render_dump.bak
   ```

5. Check the Alembic revision and compare important row counts on both databases:

   ```powershell
   psql -d "$env:RENDER_DATABASE_URL" -c "SELECT version_num FROM alembic_version;"
   psql -d "$env:NEON_MIGRATION_DATABASE_URL" -c "SELECT version_num FROM alembic_version;"

   $counts = @"
   SELECT 'users' AS table_name, count(*) FROM users
   UNION ALL SELECT 'projects', count(*) FROM projects
   UNION ALL SELECT 'evaluation_runs', count(*) FROM evaluation_runs
   UNION ALL SELECT 'evaluation_results', count(*) FROM evaluation_results
   ORDER BY table_name;
   "@
   psql -d "$env:RENDER_DATABASE_URL" -c $counts
   psql -d "$env:NEON_MIGRATION_DATABASE_URL" -c $counts
   ```

6. Sync the updated Blueprint so `DATABASE_URL` is no longer managed by `evalpulse-db`. The sync
   retains the existing database and does not delete its data.
7. In the Render API's **Environment** page, set:
   - `DATABASE_URL` to the Neon **pooled** connection string;
   - `MIGRATION_DATABASE_URL` to the Neon **direct** connection string.
   Deploy the API; startup applies any migrations newer than the dump.
8. Verify `/health/ready`, the demo login, existing projects and runs, and the smoke workflow.
9. Remove the temporary shell variables and protect or securely delete `render_dump.bak`.
10. After verification, delete `evalpulse-db` manually in Render. Removing it from `render.yaml` does
    not delete the existing resource during a Blueprint sync.

Keep the Render database until verification is complete so rollback only requires restoring its URL
in the two API environment variables and redeploying.

## Cost and limitations

Neon provides the durable PostgreSQL service; Render's free API, web, and Key Value resources still
have free-tier limitations. To avoid a paid background-worker instance, the API container also starts
a single Celery worker. The web proxy reaches the API through its public Render URL because free web
services cannot receive private-network traffic.

Free Key Value is non-persistent, so active jobs can be interrupted by a queue restart. Completed runs
remain in Neon. Free web services can cold-start after inactivity, and API and worker capacity are
shared. For a larger deployment, use a persistent queue and restore the dedicated worker service from
`services/worker/Dockerfile`.
