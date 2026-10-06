from fastapi import APIRouter
from sqlalchemy import select

from ..ingestion import runner, service
from ..models import Repository
from ..schemas import RepositoryCreate, RepositoryOut
from .deps import RepoDep, SessionDep

router = APIRouter(prefix="/repositories", tags=["repositories"])


@router.post("", status_code=202, response_model=RepositoryOut)
def add_repository(body: RepositoryCreate, session: SessionDep):
    """Register a local repository and start (or incrementally update) its analysis."""
    repo = service.register_repository(session, body.path)
    runner.start_analysis(repo.id)
    session.refresh(repo)
    return repo


@router.get("", response_model=list[RepositoryOut])
def list_repositories(session: SessionDep):
    return session.scalars(select(Repository).order_by(Repository.name, Repository.id)).all()


@router.get("/{repo_id}", response_model=RepositoryOut)
def get_repository(repo: RepoDep):
    return repo


@router.post("/{repo_id}/analyze", status_code=202, response_model=RepositoryOut)
def analyze(repo: RepoDep, session: SessionDep):
    runner.start_analysis(repo.id)
    session.refresh(repo)
    return repo
