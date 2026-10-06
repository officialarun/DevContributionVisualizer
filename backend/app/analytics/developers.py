from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Commit, CommitFile, Developer
from .filters import Filters, commit_conditions


def developer_stats(session: Session, repo_id: int, f: Filters) -> list[dict]:
    """Per-developer metrics. Honors the date range *and* the developer filter."""
    conds = commit_conditions(repo_id, f)
    rows = session.execute(
        select(
            Developer.id,
            Developer.name,
            Developer.email,
            func.count().label("commits"),
            func.coalesce(func.sum(Commit.additions), 0).label("additions"),
            func.coalesce(func.sum(Commit.deletions), 0).label("deletions"),
            func.min(Commit.authored_at).label("first"),
            func.max(Commit.authored_at).label("last"),
        )
        .join(Developer, Developer.id == Commit.developer_id)
        .where(*conds)
        .group_by(Developer.id)
    ).all()
    files = dict(
        session.execute(
            select(Commit.developer_id, func.count(func.distinct(CommitFile.file_id)))
            .join(CommitFile, CommitFile.commit_id == Commit.id)
            .where(*conds)
            .group_by(Commit.developer_id)
        ).all()
    )
    out = [
        {
            "id": r.id,
            "name": r.name,
            "email": r.email,
            "commits": r.commits,
            "additions": int(r.additions),
            "deletions": int(r.deletions),
            "files_touched": files.get(r.id, 0),
            "first_commit_at": r.first,
            "last_commit_at": r.last,
        }
        for r in rows
    ]
    out.sort(key=lambda d: (-d["commits"], d["name"].lower()))
    return out
