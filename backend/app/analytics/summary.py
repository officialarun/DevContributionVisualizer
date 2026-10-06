from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Commit, CommitFile
from .filters import Filters, commit_conditions


def repository_summary(session: Session, repo_id: int, f: Filters) -> dict:
    conds = commit_conditions(repo_id, f)
    commits, developers, additions, deletions, first, last = session.execute(
        select(
            func.count(),
            func.count(func.distinct(Commit.developer_id)),
            func.coalesce(func.sum(Commit.additions), 0),
            func.coalesce(func.sum(Commit.deletions), 0),
            func.min(Commit.authored_at),
            func.max(Commit.authored_at),
        ).where(*conds)
    ).one()
    files = session.scalar(
        select(func.count(func.distinct(CommitFile.file_id)))
        .join(Commit, Commit.id == CommitFile.commit_id)
        .where(*conds)
    )
    return {
        "commits": commits,
        "developers": developers,
        "files_modified": files,
        "additions": int(additions),
        "deletions": int(deletions),
        "first_commit_at": first,
        "last_commit_at": last,
    }
