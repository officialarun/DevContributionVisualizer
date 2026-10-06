"""Git extraction: spawn git, stream its output, yield typed records.

This module knows Git's output format and nothing about the database.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import uuid
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

CHUNK = 1 << 20
_ENV = {"GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0", "LC_ALL": "C"}


class GitError(Exception):
    pass


@dataclass(frozen=True)
class FileChange:
    path: str
    additions: int
    deletions: int
    is_binary: bool = False
    old_path: str | None = None  # set when git detected a rename


@dataclass
class CommitRecord:
    sha: str
    author_name: str
    author_email: str  # lowercased
    authored_at: datetime  # timezone-aware
    message: str
    files: list[FileChange] = field(default_factory=list)

    @property
    def additions(self) -> int:
        return sum(f.additions for f in self.files)

    @property
    def deletions(self) -> int:
        return sum(f.deletions for f in self.files)

    @property
    def files_changed(self) -> int:
        return len(self.files)


# --------------------------------------------------------------------------- parsing


def _text(b: bytes) -> str:
    return b.decode("utf-8", errors="replace")


def _parse_numstat(tail: bytes) -> list[FileChange]:
    """`-z` numstat: `adds\\tdels\\tpath\\0` or, for renames, `adds\\tdels\\t\\0old\\0new\\0`."""
    tokens = tail.split(b"\0")
    files: list[FileChange] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        i += 1
        if not tok.strip(b"\n"):
            continue
        tok = tok.lstrip(b"\n")
        adds, dels, path = tok.split(b"\t", 2)
        old_path = None
        if path == b"":  # rename: next two tokens are old and new path
            old_path, path = _text(tokens[i]), tokens[i + 1]
            i += 2
        binary = adds == b"-" or dels == b"-"
        files.append(
            FileChange(
                path=_text(path),
                additions=0 if binary else int(adds),
                deletions=0 if binary else int(dels),
                is_binary=binary,
                old_path=old_path,
            )
        )
    return files


def _parse_record(raw: bytes) -> CommitRecord:
    sha, name, email, date, rest = raw.split(b"\x1f", 4)
    # The message cannot contain NUL, so the first "\x1f\0" ends the header.
    message, _, tail = rest.partition(b"\x1f\0")
    return CommitRecord(
        sha=_text(sha),
        author_name=_text(name),
        author_email=_text(email).lower(),
        authored_at=datetime.fromisoformat(_text(date)),
        message=_text(message).rstrip("\n"),
        files=_parse_numstat(tail),
    )


def parse_stream(chunks: Iterable[bytes], marker: bytes) -> Iterator[CommitRecord]:
    """Incrementally parse log output where every record starts with `marker`."""
    buf = b""
    for chunk in chunks:
        buf += chunk
        parts = buf.split(marker)
        buf = parts.pop()  # last part may be incomplete
        for part in parts:
            if part:
                yield _parse_record(part)
    if buf:  # final record (its marker was consumed by the split above)
        yield _parse_record(buf)


# --------------------------------------------------------------------------- git calls


def _git(repo: Path | str, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        check=False,
        env={**os.environ, **_ENV},
    )
    if proc.returncode != 0:
        raise GitError(_text(proc.stderr).strip() or f"git {args[0]} failed")
    return _text(proc.stdout).strip()


def toplevel(path: str | Path) -> Path:
    p = Path(path).expanduser().resolve()
    if not p.is_dir():
        raise GitError(f"Not a directory: {p}")
    return Path(_git(p, "rev-parse", "--show-toplevel"))


def rev_parse(repo: Path | str, ref: str) -> str:
    return _git(repo, "rev-parse", "--verify", f"{ref}^{{commit}}")


def is_shallow(repo: Path | str) -> bool:
    return _git(repo, "rev-parse", "--is-shallow-repository") == "true"


def is_ancestor(repo: Path | str, ancestor: str, descendant: str) -> bool:
    proc = subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor", ancestor, descendant],
        capture_output=True,
        check=False,
        env={**os.environ, **_ENV},
    )
    return proc.returncode == 0


def count_commits(repo: Path | str, rev_range: str) -> int:
    return int(_git(repo, "rev-list", "--count", "--no-merges", rev_range))


def iter_commits(repo: Path | str, rev_range: str) -> Iterator[CommitRecord]:
    """Stream non-merge commits in `rev_range` (newest first) from a single git process."""
    marker = b"\x1e" + uuid.uuid4().hex.encode()
    # Per commit: <marker><H>\x1f<aN>\x1f<aE>\x1f<aI>\x1f<B>\x1f, then -z adds a NUL.
    fmt = "%x1e" + marker[1:].decode() + "%H%x1f%aN%x1f%aE%x1f%aI%x1f%B%x1f"
    cmd = [
        "git", "-C", str(repo), "log", rev_range,
        "--no-merges", "--use-mailmap", "-M", "--numstat", "-z", f"--format={fmt}",
    ]  # fmt: skip
    with tempfile.TemporaryFile() as err:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=err, env={**os.environ, **_ENV})
        assert proc.stdout is not None
        try:
            yield from parse_stream(iter(lambda: proc.stdout.read(CHUNK), b""), marker)
        finally:
            proc.stdout.close()
            rc = proc.wait()
        if rc != 0:
            err.seek(0)
            raise GitError(_text(err.read()).strip() or "git log failed")
