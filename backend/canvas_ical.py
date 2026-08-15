"""
Canvas assignment sync via the personal .ics calendar feed (Calendar ->
Calendar Feed in Canvas), NOT the Canvas REST API — UTD has disabled
self-service API tokens for students, but the per-user .ics feed URL is a
separate feature that isn't gated by that restriction.

Requires CANVAS_ICAL_URL to be set in the environment to the user's real
feed URL. Untested against real UTD Canvas data — Canvas access for the
Fall 2026 term opens 2026-08-24 per UTD's migration timeline.
"""

import os
import re
from datetime import datetime, timedelta, timezone, date as date_cls

import requests
from icalendar import Calendar
from sqlalchemy.orm import Session

from models import AssignmentCache

CANVAS_ICAL_URL = os.getenv("CANVAS_ICAL_URL")

# Canvas formats assignment SUMMARY as "Title [Course Short Name]".
_COURSE_SUFFIX_RE = re.compile(r"^(?P<title>.*?)\s*\[(?P<course>[^\]]+)\]\s*$")


def _to_utc_datetime(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if isinstance(value, date_cls):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    return None


def _fetch_ics_bytes() -> bytes:
    if not CANVAS_ICAL_URL:
        raise RuntimeError("CANVAS_ICAL_URL is not set in the environment.")
    resp = requests.get(CANVAS_ICAL_URL, timeout=20)
    resp.raise_for_status()
    return resp.content


def sync_assignments(db: Session) -> int:
    calendar = Calendar.from_ical(_fetch_ics_bytes())

    synced = 0
    for component in calendar.walk():
        if component.name != "VEVENT":
            continue

        uid = str(component.get("uid") or "").strip()
        if not uid:
            continue

        raw_summary = str(component.get("summary") or "").strip()
        match = _COURSE_SUFFIX_RE.match(raw_summary)
        title = match.group("title") if match else raw_summary
        course_name = match.group("course") if match else None

        dtstart = component.get("dtstart")
        due_at = _to_utc_datetime(dtstart.dt) if dtstart else None

        description = str(component.get("description") or "") or None
        html_url = str(component.get("url") or "") or None

        row = db.query(AssignmentCache).filter(AssignmentCache.canvas_uid == uid).first()
        if row is None:
            row = AssignmentCache(canvas_uid=uid)
            db.add(row)

        row.course_name = course_name
        row.title = title or raw_summary or "Untitled assignment"
        row.due_at = due_at
        row.description = description
        row.html_url = html_url
        row.synced_at = datetime.utcnow()
        synced += 1

    db.commit()
    return synced


def get_due_this_week(db: Session) -> list[AssignmentCache]:
    now = datetime.now(timezone.utc)
    week_out = now + timedelta(days=7)
    return (
        db.query(AssignmentCache)
        .filter(AssignmentCache.due_at.isnot(None))
        .filter(AssignmentCache.due_at >= now)
        .filter(AssignmentCache.due_at <= week_out)
        .order_by(AssignmentCache.due_at)
        .all()
    )


def get_due_today(db: Session) -> list[AssignmentCache]:
    now = datetime.now(timezone.utc)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)
    return (
        db.query(AssignmentCache)
        .filter(AssignmentCache.due_at.isnot(None))
        .filter(AssignmentCache.due_at >= start_of_day)
        .filter(AssignmentCache.due_at < end_of_day)
        .order_by(AssignmentCache.due_at)
        .all()
    )
