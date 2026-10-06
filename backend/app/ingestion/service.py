"""Persist git history into the database. Idempotent, batched, incremental."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from itertools import islice
from pathlib import Path

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from ..config import settings
from ..errors import InvalidRepository, NotFound
from ..models import Commit, CommitFile, Developer, File, Repository
from . import git_log
from .git_log import CommitRecord, GitError

PATH_LOOKUP_CHUNK = 5000


def resolve_repo_path(path: str) -> Path:
    try:
        top = git_log.toplevel(path)
    except GitError as e:
        raise InvalidRepository(f"Not a usable git repository: {e}") from e
    roots = settings.allowed_roots
    if roots and not any(top == r or r in top.parents for r in roots):
        raise InvalidRepository("Repository is outside the allowed roots")
    return top


def register_repository(session: Session, path: str) -> Repository:
    top = resolve_repo_path(path)
    repo = session.scalar(select(Repository).where(Repository.path == str(top)))
    if repo is None:
        repo = Repository(path=str(top), name=top.name)
        session.add(repo)
        session.commit()
    return repo


def claim(session: Session, repo_id: int) -> bool:
    """Atomically move a repository to `running`. False if it already is."""
    res = session.execute(
        update(Repository)
        .where(Repository.id == repo_id, Repository.status != "running")
        .values(status="running", error=None, commits_processed=0, commits_total=0)
    )
    session.commit()
    return res.rowcount == 1


def reset_stale_running(session: Session) -> None:
    """A `running` row at process start means the previous process died mid-run."""
    session.execute(
        update(Repository)
        .where(Repository.status == "running")
        .values(status="failed", error="Interrupted; re-run the analysis")
    )
    session.commit()


def _batches(it: Iterable[CommitRecord], size: int):
    it = iter(it)
    while batch := list(islice(it, size)):
        yield batch


def run_analysis(
    session_factory: sessionmaker[Session],
    repo_id: int,
    on_progress: Callable[[int, int], None] | None = None,
) -> None:
    """Analyze a repository that has already been `claim`ed. Never raises; records failure."""
    with session_factory() as session:
        try:
            _analyze(session, repo_id, on_progress)
        except Exception as e:  # noqa: BLE001 - failure is recorded on the repository row
            session.rollback()
            session.execute(
                update(Repository)
                .where(Repository.id == repo_id)
                .values(status="failed", error=str(e)[:2000])
            )
            session.commit()


def _analyze(session: Session, repo_id: int, on_progress) -> None:
    repo = session.get(Repository, repo_id)
    if repo is None:
        raise NotFound(f"Repository {repo_id} not found")
    path = repo.path

    head = git_log.rev_parse(path, repo.ref)
    shallow = git_log.is_shallow(path)
    last = repo.last_analyzed_sha

    if last and git_log.is_ancestor(path, last, head):
        rev_range = None if last == head else f"{last}..{head}"  # None: nothing new
    else:
        if last:  # history was rewritten: start over
            _wipe(session, repo_id)
        rev_range = head

    total = git_log.count_commits(path, rev_range) if rev_range else 0
    repo.commits_total = total
    repo.commits_processed = 0
    session.commit()

    if rev_range:
        dev_cache: dict[str, int] = {}
        file_cache: dict[str, int] = {}
        done = 0
        for batch in _batches(git_log.iter_commits(path, rev_range), settings.batch_size):
            _persist_batch(session, repo_id, batch, dev_cache, file_cache)
            done += len(batch)
            session.execute(
                update(Repository).where(Repository.id == repo_id).values(commits_processed=done)
            )
            session.commit()
            if on_progress:
                on_progress(done, total)

    session.execute(
        update(Repository)
        .where(Repository.id == repo_id)
        .values(
            status="ready",
            error=None,
            last_analyzed_sha=head,
            last_analyzed_at=datetime.now(UTC),
            is_shallow=shallow,
        )
    )
    session.commit()


def _wipe(session: Session, repo_id: int) -> None:
    for model in (Commit, File, Developer):  # commit_files cascade from commits/files
        session.execute(delete(model).where(model.repository_id == repo_id))
    session.commit()


def _persist_batch(
    session: Session,
    repo_id: int,
    batch: list[CommitRecord],
    dev_cache: dict[str, int],
    file_cache: dict[str, int],
) -> None:
    # Developers. The log is newest-first, so the first name seen per run is the latest.
    new_devs: dict[str, str] = {}
    for rec in batch:
        if rec.author_email not in dev_cache and rec.author_email not in new_devs:
            new_devs[rec.author_email] = rec.author_name
    if new_devs:
        stmt = insert(Developer).values(
            [{"repository_id": repo_id, "email": e, "name": n} for e, n in new_devs.items()]
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["repository_id", "email"], set_={"name": stmt.excluded.name}
        ).returning(Developer.id, Developer.email)
        for dev_id, email in session.execute(stmt):
            dev_cache[email] = dev_id

    # Files.
    new_paths = {f.path for rec in batch for f in rec.files if f.path not in file_cache}
    if new_paths:
        paths = sorted(new_paths)
        for i in range(0, len(paths), PATH_LOOKUP_CHUNK):
            chunk = paths[i : i + PATH_LOOKUP_CHUNK]
            session.execute(
                insert(File)
                .values([{"repository_id": repo_id, "path": p} for p in chunk])
                .on_conflict_do_nothing(index_elements=["repository_id", "path"])
            )
            rows = session.execute(
                select(File.id, File.path).where(
                    File.repository_id == repo_id, File.path.in_(chunk)
                )
            )
            file_cache.update({p: fid for fid, p in rows})

    # Commits. RETURNING only yields rows actually inserted, so already-stored commits
    # (a re-run) are skipped along with their files.
    stmt = (
        insert(Commit)
        .values(
            [
                {
                    "repository_id": repo_id,
                    "sha": rec.sha,
                    "developer_id": dev_cache[rec.author_email],
                    "authored_at": rec.authored_at,
                    "message": rec.message,
                    "files_changed": rec.files_changed,
                    "additions": rec.additions,
                    "deletions": rec.deletions,
                }
                for rec in batch
            ]
        )
        .on_conflict_do_nothing(index_elements=["repository_id", "sha"])
        .returning(Commit.id, Commit.sha)
    )
    commit_ids = {sha: cid for cid, sha in session.execute(stmt)}

    cf_rows = [
        {
            "commit_id": commit_ids[rec.sha],
            "file_id": file_cache[f.path],
            "additions": f.additions,
            "deletions": f.deletions,
            "is_binary": f.is_binary,
            "old_path": f.old_path,
        }
        for rec in batch
        if rec.sha in commit_ids
        for f in rec.files
    ]
    if cf_rows:
        session.execute(insert(CommitFile).on_conflict_do_nothing(), cf_rows)
