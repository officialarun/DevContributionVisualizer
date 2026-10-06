from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(primary_key=True)
    path: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(String(255))
    ref: Mapped[str] = mapped_column(String(255), default="HEAD")
    status: Mapped[str] = mapped_column(
        String(16), default="pending"
    )  # pending|running|ready|failed
    error: Mapped[str | None] = mapped_column(Text)
    commits_total: Mapped[int] = mapped_column(Integer, default=0)
    commits_processed: Mapped[int] = mapped_column(Integer, default=0)
    last_analyzed_sha: Mapped[str | None] = mapped_column(String(64))
    last_analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_shallow: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Developer(Base):
    __tablename__ = "developers"
    __table_args__ = (UniqueConstraint("repository_id", "email"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id", ondelete="CASCADE"))
    email: Mapped[str] = mapped_column(String(320))  # lowercased
    name: Mapped[str] = mapped_column(String(255))  # latest seen


class Commit(Base):
    __tablename__ = "commits"
    __table_args__ = (
        UniqueConstraint("repository_id", "sha"),
        Index("ix_commits_repo_authored", "repository_id", "authored_at"),
        Index("ix_commits_repo_dev_authored", "repository_id", "developer_id", "authored_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id", ondelete="CASCADE"))
    sha: Mapped[str] = mapped_column(String(64))
    developer_id: Mapped[int] = mapped_column(ForeignKey("developers.id", ondelete="CASCADE"))
    authored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    message: Mapped[str] = mapped_column(Text)
    files_changed: Mapped[int] = mapped_column(Integer, default=0)
    additions: Mapped[int] = mapped_column(Integer, default=0)
    deletions: Mapped[int] = mapped_column(Integer, default=0)


class File(Base):
    __tablename__ = "files"
    __table_args__ = (UniqueConstraint("repository_id", "path"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id", ondelete="CASCADE"))
    path: Mapped[str] = mapped_column(Text)


class CommitFile(Base):
    __tablename__ = "commit_files"
    __table_args__ = (Index("ix_commit_files_file", "file_id"),)

    commit_id: Mapped[int] = mapped_column(
        ForeignKey("commits.id", ondelete="CASCADE"), primary_key=True
    )
    file_id: Mapped[int] = mapped_column(
        ForeignKey("files.id", ondelete="CASCADE"), primary_key=True
    )
    additions: Mapped[int] = mapped_column(Integer, default=0)
    deletions: Mapped[int] = mapped_column(Integer, default=0)
    is_binary: Mapped[bool] = mapped_column(Boolean, default=False)
    old_path: Mapped[str | None] = mapped_column(Text)
