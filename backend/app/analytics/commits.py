from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..errors import NotFound
from ..models import Commit, CommitFile, Developer, File
from .filters import Filters, commit_conditions, escape_like


def _commit_row(c: Commit, dev: Developer) -> dict:
    return {
        "sha": c.sha,
        "short_sha": c.sha[:7],
        "author_name": dev.name,
        "author_email": dev.email,
        "developer_id": dev.id,
        "authored_at": c.authored_at,
        "message": c.message,
        "files_changed": c.files_changed,
        "additions": c.additions,
        "deletions": c.deletions,
    }


def list_commits(
    session: Session, repo_id: int, f: Filters, *, q: str | None, limit: int, offset: int
) -> dict:
    conds = commit_conditions(repo_id, f)
    if q:
        like = f"%{escape_like(q)}%"
        conds.append(
            or_(
                Commit.message.ilike(like, escape="\\"),
                Commit.sha.startswith(q.lower()),
                Developer.name.ilike(like, escape="\\"),
            )
        )
    base = select(Commit, Developer).join(Developer, Developer.id == Commit.developer_id)
    total = session.scalar(
        select(func.count())
        .select_from(Commit)
        .join(Developer, Developer.id == Commit.developer_id)
        .where(*conds)
    )
    rows = session.execute(
        base.where(*conds)
        .order_by(Commit.authored_at.desc(), Commit.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return {"total": total, "items": [_commit_row(c, d) for c, d in rows]}


def commit_detail(session: Session, repo_id: int, sha: str) -> dict:
    matches = session.execute(
        select(Commit, Developer)
        .join(Developer, Developer.id == Commit.developer_id)
        .where(Commit.repository_id == repo_id, Commit.sha.startswith(sha.lower()))
        .limit(2)
    ).all()
    if len(matches) != 1:
        raise NotFound(
            f"Commit {sha} not found" if not matches else f"Ambiguous commit prefix {sha}"
        )
    c, dev = matches[0]
    files = session.execute(
        select(
            File.path,
            CommitFile.old_path,
            CommitFile.additions,
            CommitFile.deletions,
            CommitFile.is_binary,
        )
        .join(CommitFile, CommitFile.file_id == File.id)
        .where(CommitFile.commit_id == c.id)
        .order_by(File.path)
    ).all()
    return {
        **_commit_row(c, dev),
        "files": [
            {"path": p, "old_path": o, "additions": a, "deletions": d, "is_binary": b}
            for p, o, a, d, b in files
        ],
    }
