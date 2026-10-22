# Developer Contribution Visualizer

Analyze a local Git repository and explore who contributed, how much, when, and to which files.
It reports Git *activity* (commits, lines added/deleted, files touched) — not productivity or the
value of anyone's work. See [Architecture.md](Architecture.md) for the design.

## Run it

Requirements: Python ≥ 3.11 with [uv](https://docs.astral.sh/uv/), Node ≥ 20, Docker, git.

```bash
cp .env.example .env     # defaults match docker-compose.yml
make db                  # PostgreSQL on 127.0.0.1:5433
make migrate
make build               # build the frontend
make api                 # http://127.0.0.1:8000  (API + built frontend)
```

Open http://127.0.0.1:8000, enter the absolute path of a local repository and click **Analyze**.
Or from the terminal: `make analyze REPO=/path/to/repo`. Analyzing again only reads new commits.

Development: `make api` and `make web` (Vite on http://localhost:5173, proxying `/api`).

## Tests

`make test` — builds a synthetic repository with hand-computed expectations (renames, binary files,
mailmap, merges, time zones) and checks ingestion, incremental runs, analytics and the API.

## Notes

- Merge commits are skipped; developers are identified by (mailmap-aware) email, so one person
  using several emails appears as several developers unless a `.mailmap` maps them.
- Lines include generated, vendored and lock files.
- Runs a single API worker (ingestion is in-process). Binds to localhost; no authentication in V1.
