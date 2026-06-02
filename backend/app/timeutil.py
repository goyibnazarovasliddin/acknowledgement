"""
Time display helpers.

DB stores naive UTC (datetime.utcnow). For display/export we convert to the
configured fixed offset (Asia/Tashkent / Ashgabat = UTC+5, no DST) so every
viewer sees the same wall-clock time regardless of their device.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.config import settings

_OFFSET = timezone(timedelta(hours=settings.TZ_OFFSET_HOURS))


def to_local(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_OFFSET)


def fmt_local(dt: Optional[datetime], fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    loc = to_local(dt)
    return loc.strftime(fmt) if loc else ""
