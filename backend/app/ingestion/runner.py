"""Run an analysis on a background thread (single-process; no job queue in V1)."""

import threading

from ..db import SessionLocal
from ..errors import AlreadyRunning, NotFound
from ..models import Repository
from . import service


def start_analysis(repo_id: int) -> None:
    with SessionLocal() as session:
        if session.get(Repository, repo_id) is None:
            raise NotFound(f"Repository {repo_id} not found")
        if not service.claim(session, repo_id):
            raise AlreadyRunning("An analysis is already running for this repository")
    threading.Thread(target=service.run_analysis, args=(SessionLocal, repo_id), daemon=True).start()
