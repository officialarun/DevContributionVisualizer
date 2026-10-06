import os
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models import Base


def git(repo: Path, *args: str, env: dict | None = None) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null", **(env or {})},
    ).stdout


def commit(repo: Path, who: str, email: str, date: str, msg: str, *extra: str) -> None:
    git(repo, "add", "-A", ":!.mailmap")
    env = {
        "GIT_AUTHOR_NAME": who,
        "GIT_AUTHOR_EMAIL": email,
        "GIT_COMMITTER_NAME": who,
        "GIT_COMMITTER_EMAIL": email,
        "GIT_AUTHOR_DATE": date,
        "GIT_COMMITTER_DATE": date,
    }
    git(repo, "commit", "-q", "--allow-empty", "-m", msg, *extra, env=env)


def build_sample_repo(root: Path) -> Path:
    """Known history (all values hand-computed in the tests):

    C1 Alice 2024-01-01T10:00Z  +a.txt(10) +docs/b.md(4)            +14 -0  2 files
    C2 Bob   2024-01-02T09:00Z  a.txt (+3 -2), +"dé r/ü.txt"(1)      +4  -2  2 files
    C3 Alice 2024-01-05T12:00Z  rename docs/b.md->docs/c.md, +img.bin (binary)  +0 -0  2 files
    C4 Alice(alt email, mailmapped) 2024-01-05T23:30-05:00 (=01-06 04:30Z)  a.txt +1   +1 -0
    F1 Bob   2024-01-10T08:00Z  feature branch: +feat.txt(2)          +2  -0  1 file
    M  Alice 2024-01-11         --no-ff merge (excluded from analysis)
    """
    repo = root / "sample"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "master")
    (repo / ".mailmap").write_text("Alice <alice@example.com> <alice@alt.com>\n")  # untracked

    (repo / "a.txt").write_text("".join(f"l{i}\n" for i in range(1, 11)))
    (repo / "docs").mkdir()
    (repo / "docs/b.md").write_text("b1\nb2\nb3\nb4\n")
    commit(
        repo, "Alice", "Alice@Example.com", "2024-01-01T10:00:00+00:00", "init\n\nmultiline body"
    )

    (repo / "a.txt").write_text("".join(f"l{i}\n" for i in range(1, 9)) + "n1\nn2\nn3\n")
    (repo / "dé r").mkdir()
    (repo / "dé r/ü.txt").write_text("hi\n")
    commit(repo, "Bob", "BOB@example.com", "2024-01-02T09:00:00+00:00", "tweak a")

    git(repo, "mv", "docs/b.md", "docs/c.md")
    (repo / "img.bin").write_bytes(bytes(range(256)) * 4)
    commit(repo, "Alice", "alice@example.com", "2024-01-05T12:00:00+00:00", "rename + binary")

    with (repo / "a.txt").open("a") as f:
        f.write("z\n")
    commit(repo, "Alicia", "alice@alt.com", "2024-01-05T23:30:00-05:00", "alt email")

    git(repo, "checkout", "-q", "-b", "feature")
    (repo / "feat.txt").write_text("f1\nf2\n")
    commit(repo, "Bob", "bob@example.com", "2024-01-10T08:00:00+00:00", "feature")
    git(repo, "checkout", "-q", "master")
    env = {
        "GIT_AUTHOR_NAME": "Alice", "GIT_AUTHOR_EMAIL": "alice@example.com",
        "GIT_COMMITTER_NAME": "Alice", "GIT_COMMITTER_EMAIL": "alice@example.com",
        "GIT_AUTHOR_DATE": "2024-01-11T08:00:00+00:00", "GIT_COMMITTER_DATE": "2024-01-11T08:00:00+00:00",
    }  # fmt: skip
    git(repo, "merge", "--no-ff", "-q", "-m", "merge feature", "feature", env=env)
    return repo


@pytest.fixture(scope="session")
def sample_repo(tmp_path_factory) -> Path:
    return build_sample_repo(tmp_path_factory.mktemp("repos"))


@pytest.fixture(scope="session")
def test_engine():
    url = make_url(settings.database_url)
    admin = create_engine(url, isolation_level="AUTOCOMMIT")
    with admin.connect() as c:
        if not c.scalar(text("select 1 from pg_database where datname='contrib_test'")):
            c.execute(text("create database contrib_test"))
    admin.dispose()
    engine = create_engine(url.set(database="contrib_test"))
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session_factory(test_engine):
    with test_engine.begin() as c:
        c.execute(text("truncate repositories restart identity cascade"))
    return sessionmaker(test_engine, expire_on_commit=False)


@pytest.fixture
def session(session_factory):
    with session_factory() as s:
        yield s
