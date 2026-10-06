from datetime import date
from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from ..analytics.filters import Filters
from ..db import get_session
from ..errors import InvalidFilter, NotFound
from ..models import Repository

SessionDep = Annotated[Session, Depends(get_session)]


def get_filters(
    date_from: Annotated[
        date | None, Query(alias="from", description="UTC date, inclusive")
    ] = None,
    date_to: Annotated[date | None, Query(alias="to", description="UTC date, inclusive")] = None,
    developer_id: Annotated[list[int] | None, Query()] = None,
) -> Filters:
    if date_from and date_to and date_from > date_to:
        raise InvalidFilter("`from` must not be after `to`")
    return Filters(date_from, date_to, tuple(developer_id or ()))


FiltersDep = Annotated[Filters, Depends(get_filters)]


def get_repository(repo_id: int, session: SessionDep) -> Repository:
    repo = session.get(Repository, repo_id)
    if repo is None:
        raise NotFound(f"Repository {repo_id} not found")
    return repo


RepoDep = Annotated[Repository, Depends(get_repository)]
