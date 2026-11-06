# CampusKart Supabase migration handoff

Use this file as the starting reference when reopening this work in VS Code or
a new chat. It records the agreed scope and the current implementation state;
it is not a substitute for reviewing the actual source changes.

## Agreed scope

- Move the app from MySQL/custom authentication to PostgreSQL and Supabase Auth.
- Support Supabase email/password and Google sign-in.
- Start with a fresh user base and create a new admin. Do not migrate old user
  accounts or user-linked data.
- Optionally migrate categories and products only.

## Current implementation areas

- `backend/migrations/versions/0031_supabase_auth.py` — links CampusKart
  profiles to Supabase Auth UUIDs, removes app-managed password/session tables,
  and enables RLS on app tables.
- `backend/app/api/auth_deps.py` — verifies Supabase JWTs and reads CampusKart
  roles from the application database.
- `backend/scripts/create_admin.py` — creates a confirmed Supabase Auth user
  and matching CampusKart admin profile.
- `backend/scripts/migrate_catalog.py` — imports categories and products only.
- `frontend/src/lib/auth.tsx` and `frontend/src/lib/supabase.ts` — browser
  session/auth integration.
- `backend/README.md` — detailed Supabase project setup and migration steps.
- `frontend/README.md` — local frontend setup and authentication notes.

The browser uses `VITE_SUPABASE_PUBLISHABLE_KEY` (legacy
`VITE_SUPABASE_ANON_KEY` remains supported). The backend admin bootstrap prefers
`SUPABASE_SECRET_KEY` and also accepts `SUPABASE_SERVICE_ROLE_KEY`. Never put a
secret/service-role key in the browser or commit environment files.

## Important workspace status

The migration changes are present locally and are uncommitted. Do not discard
or reset them during recovery. The current Git worktree includes a larger set
of migration changes than the “7 files, +122 / -49” batch shown by VS Code.
That exact editor batch could not be mapped confidently from Git status, so
this handoff intentionally does not claim which seven files it represents.
Review the VS Code diff/source control list after reopening.

## Recovering from “changes were updated after they were shown”

This message indicates the editor tried to apply edits against a stale version
of a file. It is not evidence that Supabase or a database migration is stuck.

1. Reopen or reload the affected file so the editor shows the current on-disk
   version.
2. Compare the current file with its Git diff and the intended change.
3. If an unsaved edit is missing, recover it from VS Code Timeline/Local
   History if available, then reapply only the missing part.
4. Do not accept an old full-file replacement over newer changes.
5. Confirm the result with Source Control and `git diff --check`.

## Setup sequence

Follow `backend/README.md` for exact Dashboard fields, provider redirects, and
environment setup. In short:

1. Configure Supabase Email and Google Auth providers, allowed redirects, and
   Auth email delivery.
2. Configure backend PostgreSQL/Supabase variables and frontend URL/publishable
   key in local environment files. Keep those files private.
3. From `backend`, run `alembic upgrade head` against the new Supabase database.
4. Optionally set `MYSQL_SOURCE_URL` temporarily and run
   `python -m scripts.migrate_catalog`.
5. Create the new admin with `python -m scripts.create_admin`.

Do not run the new migrations against the old MySQL database. The live Supabase
migration has not yet been verified against the user's project.

## Validation already performed

- Frontend production build passed; Vite reported a large-chunk-size warning.
- Backend Python compilation and configuration import passed.
- Current and legacy backend Supabase key settings were checked.
- `git diff --check` passed at the last status check.

Re-run relevant checks after any edits or VS Code recovery. No live Supabase
connection or end-to-end auth test has been performed.
