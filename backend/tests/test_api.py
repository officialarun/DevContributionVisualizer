import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api import deps
from app.ingestion import runner, service
from app.main import app
from app.models import Developer


@pytest.fixture
def client(session_factory, session, sample_repo, monkeypatch):
    def override():
        with session_factory() as s:
            yield s

    app.dependency_overrides[deps.get_session] = override
    monkeypatch.setattr(runner, "SessionLocal", session_factory)
    yield TestClient(app)  # no `with`: lifespan (stale-run reset) is not needed here
    app.dependency_overrides.clear()


@pytest.fixture
def repo_id(client, session_factory, session, sample_repo):
    repo = service.register_repository(session, str(sample_repo))
    assert service.claim(session, repo.id)
    service.run_analysis(session_factory, repo.id)
    return repo.id


def dev_ids(session):
    return {d.email: d.id for d in session.scalars(select(Developer))}


def url(rid, path):
    return f"/api/repositories/{rid}{path}"


def test_summary(client, repo_id):
    r = client.get(url(repo_id, "/summary")).json()
    assert (r["commits"], r["developers"], r["files_modified"], r["additions"], r["deletions"]) == (
        5,
        2,
        6,
        21,
        2,
    )
    assert r["first_commit_at"].startswith("2024-01-01T10:00:00")


def test_summary_filters(client, repo_id, session):
    ids = dev_ids(session)
    bob = client.get(
        url(repo_id, "/summary"), params={"developer_id": ids["bob@example.com"]}
    ).json()
    assert (
        bob["commits"],
        bob["developers"],
        bob["files_modified"],
        bob["additions"],
        bob["deletions"],
    ) == (2, 1, 3, 6, 2)
    # C4 is 2024-01-05 23:30 -05:00 == 2024-01-06 UTC, so a UTC `to` of Jan 5 excludes it
    one_day = client.get(
        url(repo_id, "/summary"), params={"from": "2024-01-05", "to": "2024-01-05"}
    ).json()
    assert one_day["commits"] == 1
    empty = client.get(url(repo_id, "/summary"), params={"from": "2025-01-01"}).json()
    assert (empty["commits"], empty["additions"], empty["first_commit_at"]) == (0, 0, None)


def test_developers(client, repo_id):
    devs = client.get(url(repo_id, "/developers")).json()
    assert [d["name"] for d in devs] == ["Alice", "Bob"]
    a, b = devs
    assert (a["commits"], a["additions"], a["deletions"], a["files_touched"]) == (3, 15, 0, 4)
    assert (b["commits"], b["additions"], b["deletions"], b["files_touched"]) == (2, 6, 2, 3)
    assert a["first_commit_at"].startswith("2024-01-01T10:00") and a["last_commit_at"].startswith(
        "2024-01-06T04:30"
    )
    one = client.get(url(repo_id, f"/developers/{b['id']}")).json()
    assert one == b
    assert (
        client.get(
            url(repo_id, f"/developers/{b['id']}"), params={"from": "2030-01-01"}
        ).status_code
        == 404
    )


def test_activity_day_zero_filled(client, repo_id):
    r = client.get(url(repo_id, "/activity")).json()
    assert r["granularity"] == "day"
    b = r["buckets"]
    assert [x["date"] for x in b] == [f"2024-01-{d:02d}" for d in range(1, 11)]
    assert [x["commits"] for x in b] == [1, 1, 0, 0, 1, 1, 0, 0, 0, 1]
    assert [x["additions"] for x in b] == [14, 4, 0, 0, 0, 1, 0, 0, 0, 2]
    assert [x["deletions"] for x in b] == [0, 2, 0, 0, 0, 0, 0, 0, 0, 0]


def test_activity_week_month_and_developer(client, repo_id, session):
    w = client.get(url(repo_id, "/activity"), params={"granularity": "week"}).json()["buckets"]
    assert w == [
        {"date": "2024-01-01", "commits": 4, "additions": 19, "deletions": 2},
        {"date": "2024-01-08", "commits": 1, "additions": 2, "deletions": 0},
    ]
    m = client.get(url(repo_id, "/activity"), params={"granularity": "month"}).json()["buckets"]
    assert m == [{"date": "2024-01-01", "commits": 5, "additions": 21, "deletions": 2}]
    bob = dev_ids(session)["bob@example.com"]
    d = client.get(url(repo_id, "/activity"), params={"developer_id": bob}).json()["buckets"]
    assert d[0]["date"] == "2024-01-02" and len(d) == 9
    assert sum(x["commits"] for x in d) == 2
    # explicit range extends zero-fill beyond the data
    r = client.get(
        url(repo_id, "/activity"), params={"from": "2023-12-30", "to": "2024-01-02"}
    ).json()["buckets"]
    assert [(x["date"], x["commits"]) for x in r] == [
        ("2023-12-30", 0), ("2023-12-31", 0), ("2024-01-01", 1), ("2024-01-02", 1),
    ]  # fmt: skip
    assert (
        client.get(url(repo_id, "/activity"), params={"from": "2030-01-01"}).json()["buckets"] == []
    )


def test_files(client, repo_id):
    r = client.get(url(repo_id, "/files")).json()
    assert r["total"] == 6
    top = r["items"][0]
    assert (top["path"], top["commits"], top["additions"], top["deletions"], top["developers"]) == (
        "a.txt",
        3,
        14,
        2,
        2,
    )
    docs = client.get(url(repo_id, "/files"), params={"q": "docs/"}).json()
    assert sorted(i["path"] for i in docs["items"]) == ["docs/b.md", "docs/c.md"]
    assert (
        client.get(url(repo_id, "/files"), params={"q": "%"}).json()["total"] == 0
    )  # LIKE wildcard escaped
    assert client.get(url(repo_id, "/files"), params={"q": "ü"}).json()["total"] == 1
    page = client.get(url(repo_id, "/files"), params={"limit": 2, "offset": 4}).json()
    assert page["total"] == 6 and len(page["items"]) == 2
    assert client.get(url(repo_id, "/files"), params={"sort": "bogus"}).status_code == 422


def test_commits(client, repo_id):
    r = client.get(url(repo_id, "/commits")).json()
    assert r["total"] == 5
    assert [c["message"].split("\n")[0] for c in r["items"]] == [
        "feature", "alt email", "rename + binary", "tweak a", "init",
    ]  # fmt: skip
    assert client.get(url(repo_id, "/commits"), params={"q": "TWEAK"}).json()["total"] == 1
    assert (
        client.get(url(repo_id, "/commits"), params={"q": "bob"}).json()["total"] == 2
    )  # by author name
    sha = r["items"][2]["sha"]
    assert client.get(url(repo_id, "/commits"), params={"q": sha[:8]}).json()["total"] == 1
    d = client.get(url(repo_id, f"/commits/{sha[:10]}")).json()
    assert d["short_sha"] == sha[:7] and (d["additions"], d["deletions"], d["files_changed"]) == (
        0,
        0,
        2,
    )
    assert d["files"] == [
        {
            "path": "docs/c.md",
            "old_path": "docs/b.md",
            "additions": 0,
            "deletions": 0,
            "is_binary": False,
        },
        {"path": "img.bin", "old_path": None, "additions": 0, "deletions": 0, "is_binary": True},
    ]
    assert client.get(url(repo_id, "/commits/deadbeef")).status_code == 404


def test_error_contract(client, repo_id):
    r = client.get("/api/repositories/9999/summary")
    assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"
    r = client.get(url(repo_id, "/summary"), params={"from": "2024-02-01", "to": "2024-01-01"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_filter"
    r = client.get(url(repo_id, "/summary"), params={"from": "garbage"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"
    r = client.post("/api/repositories", json={"path": "/definitely/not/here"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "invalid_repository"


def test_add_repository_runs_in_background(client, sample_repo):
    r = client.post("/api/repositories", json={"path": str(sample_repo)})
    assert r.status_code == 202
    rid = r.json()["id"]
    for _ in range(100):
        body = client.get(f"/api/repositories/{rid}").json()
        if body["status"] != "running":
            break
        time.sleep(0.05)
    assert body["status"] == "ready" and body["commits_processed"] == 5
    assert client.get("/api/repositories").json()[0]["id"] == rid
    # analyzing again is an incremental no-op; concurrent runs are refused with 409
    assert client.post(f"/api/repositories/{rid}/analyze").status_code == 202
