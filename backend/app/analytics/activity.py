from datetime import date, timedelta

from sqlalchemy import Date, cast, func, select
from sqlalchemy.orm import Session

from ..models import Commit
from .filters import Filters, commit_conditions

GRANULARITIES = ("day", "week", "month")


def auto_granularity(start: date, end: date) -> str:
    days = (end - start).days + 1
    return "day" if days <= 90 else "week" if days <= 730 else "month"


def _bucket_start(d: date, g: str) -> date:
    if g == "week":
        return d - timedelta(days=d.weekday())  # Monday
    if g == "month":
        return d.replace(day=1)
    return d


def _next(d: date, g: str) -> date:
    if g == "day":
        return d + timedelta(days=1)
    if g == "week":
        return d + timedelta(days=7)
    return date(d.year + d.month // 12, d.month % 12 + 1, 1)


def activity(session: Session, repo_id: int, f: Filters, granularity: str = "auto") -> dict:
    """Commits / lines added / lines deleted per UTC bucket, with empty buckets zero-filled."""
    conds = commit_conditions(repo_id, f)
    utc_day = cast(func.timezone("UTC", Commit.authored_at), Date)
    lo, hi = session.execute(select(func.min(utc_day), func.max(utc_day)).where(*conds)).one()
    if lo is None:
        return {"granularity": "day" if granularity == "auto" else granularity, "buckets": []}

    start = f.date_from or lo
    end = f.date_to or hi
    g = auto_granularity(start, end) if granularity == "auto" else granularity

    bucket = cast(func.date_trunc(g, func.timezone("UTC", Commit.authored_at)), Date)
    rows = {
        r.bucket: r
        for r in session.execute(
            select(
                bucket.label("bucket"),
                func.count().label("commits"),
                func.sum(Commit.additions).label("additions"),
                func.sum(Commit.deletions).label("deletions"),
            )
            .where(*conds)
            .group_by(bucket)
        )
    }
    buckets = []
    d, last = _bucket_start(start, g), _bucket_start(end, g)
    while d <= last:
        r = rows.get(d)
        buckets.append(
            {
                "date": d,
                "commits": r.commits if r else 0,
                "additions": int(r.additions) if r else 0,
                "deletions": int(r.deletions) if r else 0,
            }
        )
        d = _next(d, g)
    return {"granularity": g, "buckets": buckets}
