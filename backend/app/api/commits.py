from typing import Annotated

from fastapi import APIRouter, Query

from ..analytics import commits as commits_q
from ..schemas import CommitDetail, CommitList
from .deps import FiltersDep, RepoDep, SessionDep

router = APIRouter(prefix="/repositories/{repo_id}/commits", tags=["commits"])


@router.get("", response_model=CommitList)
def list_commits(
    repo: RepoDep,
    f: FiltersDep,
    session: SessionDep,
    q: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return commits_q.list_commits(session, repo.id, f, q=q, limit=limit, offset=offset)


@router.get("/{sha}", response_model=CommitDetail)
def commit_detail(sha: str, repo: RepoDep, session: SessionDep):
    return commits_q.commit_detail(session, repo.id, sha)
