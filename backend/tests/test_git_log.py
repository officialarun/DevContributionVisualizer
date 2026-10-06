import pytest

from app.ingestion import git_log
from app.ingestion.git_log import GitError, parse_stream


def test_parse_stream_handles_chunk_boundaries_rename_binary_and_empty_commit():
    m = b"\x1eMARK"
    raw = (
        m
        + b"a" * 40
        + b"\x1fAl\x1fAL@X.com\x1f2024-01-01T10:00:00+05:30\x1fsubject\n\nbody\n\x1f\0"
        b"3\t1\tsrc/a.py\0"
        b"0\t0\t\0old/n.py\0new/n.py\0"
        b"-\t-\timg.png\0"
        + m
        + b"b" * 40
        + b"\x1fBo\x1fbo@x.com\x1f2024-01-02T00:00:00+00:00\x1fempty\n\x1f\0"
    )
    for size in (1, 7, 64, len(raw)):  # every possible split point class
        chunks = [raw[i : i + size] for i in range(0, len(raw), size)]
        recs = list(parse_stream(chunks, m))
        assert [r.sha[0] for r in recs] == ["a", "b"]
        a, b = recs
        assert (a.author_name, a.author_email) == ("Al", "al@x.com")
        assert a.authored_at.utcoffset().total_seconds() == 5.5 * 3600
        assert a.message == "subject\n\nbody"
        assert [(f.path, f.additions, f.deletions, f.is_binary, f.old_path) for f in a.files] == [
            ("src/a.py", 3, 1, False, None),
            ("new/n.py", 0, 0, False, "old/n.py"),
            ("img.png", 0, 0, True, None),
        ]
        assert (a.additions, a.deletions, a.files_changed) == (3, 1, 3)
        assert b.files == [] and b.files_changed == 0


def test_iter_commits_on_real_repo(sample_repo):
    recs = list(git_log.iter_commits(sample_repo, "HEAD"))
    # newest first; merge commit excluded
    assert [r.message.split("\n")[0] for r in recs] == [
        "feature", "alt email", "rename + binary", "tweak a", "init",
    ]  # fmt: skip
    by_msg = {r.message.split("\n")[0]: r for r in recs}
    assert by_msg["init"].message == "init\n\nmultiline body"
    assert (by_msg["init"].additions, by_msg["init"].deletions) == (14, 0)
    assert (by_msg["tweak a"].additions, by_msg["tweak a"].deletions) == (4, 2)
    assert "dé r/ü.txt" in {f.path for f in by_msg["tweak a"].files}
    rb = by_msg["rename + binary"]
    assert {(f.path, f.old_path, f.is_binary) for f in rb.files} == {
        ("docs/c.md", "docs/b.md", False),
        ("img.bin", None, True),
    }
    assert (rb.additions, rb.deletions) == (0, 0)
    # mailmap: alt email folded into Alice's canonical identity
    assert (by_msg["alt email"].author_name, by_msg["alt email"].author_email) == (
        "Alice", "alice@example.com",
    )  # fmt: skip


def test_helpers(sample_repo):
    assert git_log.toplevel(sample_repo / "docs") == sample_repo
    head = git_log.rev_parse(sample_repo, "HEAD")
    assert len(head) == 40
    assert git_log.count_commits(sample_repo, "HEAD") == 5
    assert git_log.is_shallow(sample_repo) is False
    assert git_log.is_ancestor(sample_repo, head, head)
    with pytest.raises(GitError):
        git_log.toplevel("/tmp")
    with pytest.raises(GitError):
        list(git_log.iter_commits(sample_repo, "nonexistent-ref"))
