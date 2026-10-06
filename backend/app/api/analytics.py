from typing import Annotated, Literal

from fastapi import APIRouter, Query

from ..analytics import activity as activity_q
from ..analytics import developers as developers_q
from ..analytics import files as files_q
from ..analytics import summary as summary_q
from ..errors import NotFound
from ..schemas import Activity, DeveloperStats, FileList, Summary
from .deps import FiltersDep, RepoDep, SessionDep

router = APIRouter(prefix="/repositories/{repo_id}", tags=["analytics"])


@router.get("/summary", response_model=Summary)
def summary(repo: RepoDep, f: FiltersDep, session: SessionDep):
    return summary_q.repository_summary(session, repo.id, f)


@router.get("/developers", response_model=list[DeveloperStats])
def developers(repo: RepoDep, f: FiltersDep, session: SessionDep):
    """Per-developer metrics (ranked by commits only as a default sort, not a score)."""
    return developers_q.developer_stats(session, repo.id, f)


@router.get("/developers/{dev_id}", response_model=DeveloperStats)
def developer(dev_id: int, repo: RepoDep, f: FiltersDep, session: SessionDep):
    only = f.__class__(f.date_from, f.date_to, (dev_id,))
    rows = developers_q.developer_stats(session, repo.id, only)
    if not rows:
        raise NotFound(f"Developer {dev_id} has no commits in this range")
    return rows[0]


@router.get("/activity", response_model=Activity)
def activity(
    repo: RepoDep,
    f: FiltersDep,
    session: SessionDep,
    granularity: Literal["auto", "day", "week", "month"] = "auto",
):
    return activity_q.activity(session, repo.id, f, granularity)


@router.get("/files", response_model=FileList)
def files(
    repo: RepoDep,
    f: FiltersDep,
    session: SessionDep,
    q: str | None = None,
    sort: Literal["commits", "additions", "deletions", "developers", "last_modified"] = "commits",
    limit: Annotated[int, Query(ge=1, le=200)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return files_q.file_stats(session, repo.id, f, q=q, sort=sort, limit=limit, offset=offset)
