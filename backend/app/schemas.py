from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class RepositoryCreate(BaseModel):
    path: str


class RepositoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    path: str
    status: Literal["pending", "running", "ready", "failed"]
    error: str | None
    commits_total: int
    commits_processed: int
    last_analyzed_sha: str | None
    last_analyzed_at: datetime | None
    is_shallow: bool


class Summary(BaseModel):
    commits: int
    developers: int
    files_modified: int
    additions: int
    deletions: int
    first_commit_at: datetime | None
    last_commit_at: datetime | None


class DeveloperStats(BaseModel):
    id: int
    name: str
    email: str
    commits: int
    additions: int
    deletions: int
    files_touched: int
    first_commit_at: datetime | None
    last_commit_at: datetime | None


class ActivityBucket(BaseModel):
    date: date
    commits: int
    additions: int
    deletions: int


class Activity(BaseModel):
    granularity: Literal["day", "week", "month"]
    buckets: list[ActivityBucket]


class FileStats(BaseModel):
    id: int
    path: str
    commits: int
    additions: int
    deletions: int
    developers: int
    last_modified_at: datetime


class FileList(BaseModel):
    total: int
    items: list[FileStats]


class CommitOut(BaseModel):
    sha: str
    short_sha: str
    author_name: str
    author_email: str
    developer_id: int
    authored_at: datetime
    message: str
    files_changed: int
    additions: int
    deletions: int


class CommitList(BaseModel):
    total: int
    items: list[CommitOut]


class ChangedFile(BaseModel):
    path: str
    old_path: str | None
    additions: int
    deletions: int
    is_binary: bool


class CommitDetail(CommitOut):
    files: list[ChangedFile]
