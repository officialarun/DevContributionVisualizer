"""python -m app.cli analyze <path>"""

import argparse
import sys

from .db import SessionLocal
from .errors import AppError
from .ingestion import service


def main() -> int:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analyze", help="Analyze (or incrementally update) a local git repository")
    a.add_argument("path")
    args = parser.parse_args()

    try:
        with SessionLocal() as session:
            repo = service.register_repository(session, args.path)
            if not service.claim(session, repo.id):
                print("Analysis already running for this repository", file=sys.stderr)
                return 1
            repo_id = repo.id
    except AppError as e:
        print(f"error: {e.message}", file=sys.stderr)
        return 1

    def progress(done: int, total: int) -> None:
        print(f"\r{done}/{total} commits", end="", flush=True)

    service.run_analysis(SessionLocal, repo_id, progress)
    with SessionLocal() as session:
        from .models import Repository

        repo = session.get(Repository, repo_id)
        print()
        if repo.status != "ready":
            print(f"failed: {repo.error}", file=sys.stderr)
            return 1
        print(f"ready: repository id={repo.id} {repo.path} @ {repo.last_analyzed_sha[:10]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
