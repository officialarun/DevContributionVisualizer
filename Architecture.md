# Architecture — Developer Contribution Visualizer

Purpose: observe → measure → visualize → explore Git activity. It does **not** rank or score developers. Lines of code are not a measure of productivity or value.

## 1. Overview

```
 local git repo                       (read-only: git CLI only)
      │  one streamed `git log --numstat -z`
      ▼
 ingestion/git_log.py   pure parser: bytes → CommitRecord(+FileChange). No DB.
      │  batches of ~500 commits
      ▼
 ingestion/service.py   upserts developers/files, inserts commits + commit_files,
      │                 updates repository status / watermark
      ▼
 PostgreSQL  ◄────────── analytics/*.py   SQL aggregation, one shared Filters object
                               ▲
                         api/*.py         thin FastAPI routers
                               ▲  JSON over HTTP, /api/*
                         React SPA        never talks to git
```

Dependency rule: `api → analytics → models`; `api → ingestion.service → git_log, models`.
`git_log` imports nothing from the DB. Routers contain no Git or SQL logic.

## 2. Components

| Component | Responsibility |
|---|---|
| `ingestion/git_log.py` | Spawn `git log`, stream stdout, yield typed records. Knows Git's output format only. |
| `ingestion/service.py` | Idempotent batch persistence, progress, watermark, error capture. Used by CLI and API. |
| `ingestion/runner.py` | Runs ingestion in a background thread; prevents double runs. |
| `analytics/*` | Every metric as a SQL query function `(session, repo_id, Filters)`. The only place metrics are computed — the dashboard and developer page share them. |
| `api/*` | Validation, pagination, error mapping, OpenAPI. |
| Frontend | Global filter bar (state in URL), pages, reusable charts, query-boundary states. |

## 3. Data flow

1. `POST /api/repositories {path}` (or `python -m app.cli analyze <path>`) → validate path → upsert `repositories` → `202`.
2. Background thread: capture `head_sha`; `git rev-list --count` for the progress denominator; stream the log; batch-persist; on success set `last_analyzed_sha = head_sha`, `status = ready`.
3. Frontend polls `GET /api/repositories/{id}` until `ready`, then loads analytics endpoints.

## 4. Database schema (PostgreSQL)

```
repositories  id PK · path UNIQUE (resolved abs) · name · ref (default 'HEAD')
              status {pending,running,ready,failed} · error · commits_total · commits_processed
              last_analyzed_sha · last_analyzed_at · is_shallow · created_at
developers    id PK · repository_id FK · email (lowercased) · name (latest seen)
              UNIQUE(repository_id, email)
commits       id PK · repository_id FK · sha (UNIQUE per repo) · developer_id FK
              authored_at timestamptz · message · files_changed · additions · deletions
              INDEX(repository_id, authored_at)
              INDEX(repository_id, developer_id, authored_at)
files         id PK · repository_id FK · path · UNIQUE(repository_id, path)
commit_files  commit_id FK · file_id FK · additions · deletions · is_binary · old_path NULL
              PK(commit_id, file_id) · INDEX(file_id)
```

Why each entity exists:

- **repositories** — scope and analysis state; the incremental watermark lives here.
- **developers** — canonical identity (by lowercased email, mailmap-aware) so metrics are derived, not stored.
- **commits** — the unit of history. Denormalized totals (`additions`, `deletions`, `files_changed`) so lists and repo-level sums don't scan `commit_files`.
- **files** — normalizes path strings (millions of repeats otherwise) and anchors file analytics.
- **commit_files** — many-to-many edge carrying per-file churn.

No aggregate tables are stored: every metric derives from these, so they cannot drift.

## 5. API (`/api`, JSON)

Shared query params (one FastAPI dependency → one `Filters` dataclass): `from`, `to`, `developer_id` (repeatable).

```
POST /repositories {path}                 → 202 {id,status}
GET  /repositories                        → list (repo switcher)
GET  /repositories/{id}                   → status, progress, last_analyzed_*, warnings
POST /repositories/{id}/analyze           → incremental run (409 if running)
GET  /repositories/{id}/summary           → commits, developers, files_modified, additions, deletions, first/last
GET  /repositories/{id}/developers        → per-developer metrics
GET  /repositories/{id}/activity          → ?granularity=auto|day|week|month, zero-filled buckets
GET  /repositories/{id}/files             → ?q=&sort=commits|additions|deletions|developers&limit&offset
GET  /repositories/{id}/commits           → ?q=&limit&offset
GET  /repositories/{id}/commits/{sha}     → commit + changed files
```

The developer page uses the **same** `summary` / `activity` / `files` endpoints with `developer_id=X`. `granularity=auto`: ≤ 90 days → day, ≤ 2 years → week, otherwise month (UTC buckets).

Errors: `{"error": {"code": "...", "message": "..."}}` — 400 (invalid path / not a git repo), 404, 409 (already running), 422.

## 6. Git ingestion strategy

```
git -C <path> log <range> --no-merges --use-mailmap -M --numstat -z --format=<sentinel-delimited>
```

- `<range>` = `HEAD` (full) or `<last_sha>..<head_sha>` (incremental).
- One `subprocess.Popen` with an argv list (never a shell). Output is parsed incrementally; memory stays constant.
- Flush every ~500 commits in one transaction with `INSERT … ON CONFLICT DO NOTHING` → re-runs are idempotent.
- Merge commits are skipped (they carry no numstat and would inflate commit counts). `is_merge` can be added later.
- Renames (`-M`): the new path is the file; `old_path` is recorded; rename lineage is not followed in V1.
- Binary files (`-\t-`) → 0/0 and `is_binary = true`.
- Author identity and author date are used (not committer).
- Watermark is written only on successful completion; a crashed run is simply re-run. On startup, stale `running` rows become `failed`.
- Shallow clones are detected and surfaced as a warning.
- File contents are never read.

## 7. Frontend structure

```
/                      Repository picker / analyze form + status
/r/:id                 Dashboard
/r/:id/developers      Developer table + comparison bar chart (metric switcher)
/r/:id/developers/:dev Developer detail (same components, developer filter pinned)
/r/:id/files           Most-modified files, path search
/r/:id/commits         Commit list + search → detail
```

Dashboard: 5 summary tiles, developer table, activity line, additions-vs-deletions, top-files bar. Each chart carries a one-line caption stating the question it answers.

## 8. Visualization strategy

Small reusable SVG components: `LineChart`, `HBarChart`, (Phase 2) `CalendarHeatmap`. D3 provides scales and shape generators; React renders the SVG. Neutral wording only: *Commits, Lines added, Lines deleted, Files touched*. Default sort is by commits and labelled as such; no "top" / "best" language.

## 9. Error, loading, empty states

A single `QueryBoundary`: skeleton while loading, error card with Retry, empty state with "Clear filters". Repository states: `pending/running` → progress bar; `failed` → error + Re-analyze; shallow-clone warning banner. A persistent "About these numbers" note: lines include generated/vendored files and are not a productivity measure.

## 10. Scalability

Streaming + batches (no full-history load); one git process; indexed SQL aggregation; the dashboard reads only the DB; paginated lists. `COUNT(DISTINCT file_id)` is the heaviest query and the first rollup candidate. Growth path: daily rollup table → materialized views → partitioning `commit_files` → job queue only if multi-user. Run a single uvicorn worker (ingestion is in-process).

## 11. Incremental analysis (in V1, same code path)

`repositories.last_analyzed_sha` + `ref`. `analyze`: if `git merge-base --is-ancestor <last> <head>` → range `<last>..<head>`; otherwise (history rewritten) delete the repo's commits and run a full analysis. New developers/files are upserted on the fly.

## 12. Security

Argv-list subprocess only; paths resolved and validated as git repos; optional `ALLOWED_REPO_ROOTS`; the API binds to `127.0.0.1` by default. No auth in V1 (single-user, local).

## 13. Known limitations (V1)

Lines include generated/vendored/lockfile changes · no rename lineage · merges ignored · single branch/ref per repository · UTC bucketing · bots not distinguished.

## 14. Extension points

PRs / issues / branches → new `ingestion/` modules writing new tables; `analytics/` has one module per topic; ownership and AI insights read the same normalized tables. None block V1.

## 15. Folder structure

```
Architecture.md  README.md  Makefile  docker-compose.yml  .env.example
backend/   pyproject.toml  alembic.ini  migrations/
           app/{main,config,db,models,schemas,errors,cli}.py
           app/api/        deps.py repositories.py analytics.py commits.py
           app/ingestion/  git_log.py service.py runner.py
           app/analytics/  filters.py summary.py developers.py activity.py files.py commits.py
           tests/
frontend/  package.json vite.config.ts
           src/{api,hooks,lib,components/{layout,filters,charts,states},pages}
```
