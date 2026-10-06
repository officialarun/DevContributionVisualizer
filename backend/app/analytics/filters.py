from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta

from ..models import Commit


@dataclass(frozen=True)
class Filters:
    """The one filter object shared by every analytics query. Dates are UTC, `to` inclusive."""

    date_from: date | None = None
    date_to: date | None = None
    developer_ids: tuple[int, ...] = field(default_factory=tuple)

    @property
    def start(self) -> datetime | None:
        return datetime.combine(self.date_from, time.min, UTC) if self.date_from else None

    @property
    def end_exclusive(self) -> datetime | None:
        if not self.date_to:
            return None
        return datetime.combine(self.date_to + timedelta(days=1), time.min, UTC)

    def without_developers(self) -> "Filters":
        return Filters(self.date_from, self.date_to, ())


def commit_conditions(repo_id: int, f: Filters) -> list:
    """WHERE-clauses over `commits` implementing the filters."""
    conds = [Commit.repository_id == repo_id]
    if f.start:
        conds.append(Commit.authored_at >= f.start)
    if f.end_exclusive:
        conds.append(Commit.authored_at < f.end_exclusive)
    if f.developer_ids:
        conds.append(Commit.developer_id.in_(f.developer_ids))
    return conds


def escape_like(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
