import shutil

import pytest
from sqlalchemy import func, select

from app.errors import InvalidRepository
from app.ingestion import git_log, service
from app.models import Commit, CommitFile, Developer, File, Repository

from .conftest import commit, git


def analyze(session_factory, session, path):
    repo = service.register_repository(session, str(path))
    assert service.claim(session, repo.id)
    service.run_analysis(session_factory, repo.id)
    session.expire_all()
    return session.get(Repository, repo.id)


def counts(session):
    return tuple(
        session.scalar(select(func.count()).select_from(m))
        for m in (Commit, Developer, File, CommitFile)
    )


def test_full_analysis(session_factory, session, sample_repo):
    repo = analyze(session_factory, session, sample_repo)
    assert repo.status == "ready" and repo.error is None
    assert repo.last_analyzed_sha == git_log.rev_parse(sample_repo, "HEAD")
    assert (repo.commits_total, repo.commits_processed) == (5, 5)
    # commits, developers (Alice's alt email folded in), files (no rename lineage), commit_files
    assert counts(session) == (5, 2, 6, 8)

    devs = {d.email: d.name for d in session.scalars(select(Developer))}
    assert devs == {"alice@example.com": "Alice", "bob@example.com": "Bob"}

    rows = {c.sha: c for c in session.scalars(select(Commit))}
    by_msg = {c.message.split("\n")[0]: c for c in rows.values()}
    assert (by_msg["init"].additions, by_msg["init"].deletions, by_msg["init"].files_changed) == (
        14,
        0,
        2,
    )
    assert (by_msg["tweak a"].additions, by_msg["tweak a"].deletions) == (4, 2)
    assert by_msg["alt email"].authored_at.isoformat() == "2024-01-06T04:30:00+00:00"

    renamed = session.execute(
        select(File.path, CommitFile.old_path)
        .join(CommitFile)
        .where(CommitFile.old_path.is_not(None))
    ).all()
    assert renamed == [("docs/c.md", "docs/b.md")]
    assert session.scalar(select(func.count()).where(CommitFile.is_binary)) == 1


def test_rerun_is_idempotent_and_noop(session_factory, session, sample_repo):
    analyze(session_factory, session, sample_repo)
    before = counts(session)
    repo = analyze(session_factory, session, sample_repo)
    assert repo.status == "ready" and repo.commits_total == 0
    assert counts(session) == before


def test_incremental_processes_only_new_commits(session_factory, session, tmp_path):
    from .conftest import build_sample_repo

    path = build_sample_repo(tmp_path)
    analyze(session_factory, session, path)
    (path / "new.txt").write_text("x\ny\n")
    commit(path, "Carol", "carol@example.com", "2024-02-01T00:00:00+00:00", "carol")
    repo = analyze(session_factory, session, path)
    assert (repo.commits_total, repo.commits_processed) == (1, 1)
    assert counts(session) == (6, 3, 7, 9)
    assert repo.last_analyzed_sha == git_log.rev_parse(path, "HEAD")


def test_rewritten_history_triggers_full_reanalysis(session_factory, session, tmp_path):
    from .conftest import build_sample_repo

    path = build_sample_repo(tmp_path)
    analyze(session_factory, session, path)
    git(
        path, "reset", "-q", "--hard", "HEAD~3"
    )  # drop last commits; last_analyzed_sha no longer an ancestor
    (path / "other.txt").write_text("1\n")
    commit(path, "Dan", "dan@example.com", "2024-03-01T00:00:00+00:00", "dan")
    repo = analyze(session_factory, session, path)
    assert repo.status == "ready"
    emails = set(session.scalars(select(Developer.email)))
    assert "dan@example.com" in emails
    assert repo.commits_total == repo.commits_processed == git_log.count_commits(path, "HEAD")
    assert session.scalar(select(func.count()).select_from(Commit)) == repo.commits_total


def test_claim_is_exclusive(session_factory, session, sample_repo):
    repo = service.register_repository(session, str(sample_repo))
    assert service.claim(session, repo.id) is True
    assert service.claim(session, repo.id) is False
    service.reset_stale_running(session)
    session.expire_all()
    assert session.get(Repository, repo.id).status == "failed"


def test_invalid_path_rejected(session):
    with pytest.raises(InvalidRepository):
        service.register_repository(session, "/definitely/not/here")


def test_failure_is_recorded(session_factory, session, tmp_path):
    from .conftest import build_sample_repo

    path = build_sample_repo(tmp_path)
    repo = service.register_repository(session, str(path))
    service.claim(session, repo.id)
    shutil.rmtree(path / ".git")
    service.run_analysis(session_factory, repo.id)
    session.expire_all()
    repo = session.get(Repository, repo.id)
    assert repo.status == "failed" and repo.error
