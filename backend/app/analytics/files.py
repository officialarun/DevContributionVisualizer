from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Commit, CommitFile, File
from .filters import Filters, commit_conditions, escape_like

SORTS = ("commits", "additions", "deletions", "developers", "last_modified")


def file_stats(
    session: Session,
    repo_id: int,
    f: Filters,
    *,
    q: str | None = None,
    sort: str = "commits",
    limit: int = 20,
    offset: int = 0,
) -> dict:
    commits = func.count().label("commits")
    additions = func.sum(CommitFile.additions).label("additions")
    deletions = func.sum(CommitFile.deletions).label("deletions")
    developers = func.count(func.distinct(Commit.developer_id)).label("developers")
    last = func.max(Commit.authored_at).label("last_modified")
    order = {
        "commits": commits, "additions": additions, "deletions": deletions,
        "developers": developers, "last_modified": last,
    }[sort]  # fmt: skip

    stmt = (
        select(File.id, File.path, commits, additions, deletions, developers, last,
               func.count().over().label("total"))
        .join(CommitFile, CommitFile.file_id == File.id)
        .join(Commit, Commit.id == CommitFile.commit_id)
        .where(*commit_conditions(repo_id, f))
        .group_by(File.id)
    )  # fmt: skip
    if q:
        stmt = stmt.where(File.path.ilike(f"%{escape_like(q)}%", escape="\\"))
    # `total` is the count of groups, but window functions run before LIMIT, so it is correct.
    stmt = stmt.order_by(order.desc(), File.path).limit(limit).offset(offset)
    rows = session.execute(stmt).all()
    return {
        "total": rows[0].total if rows else 0,
        "items": [
            {
                "id": r.id,
                "path": r.path,
                "commits": r.commits,
                "additions": int(r.additions),
                "deletions": int(r.deletions),
                "developers": r.developers,
                "last_modified_at": r.last_modified,
            }
            for r in rows
        ],
    }
