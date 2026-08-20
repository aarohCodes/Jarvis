"""
CourseBook (coursebook.utdallas.edu) lookup for class schedule data.

VALIDATION STATUS (as of 2026-08-13): UNVALIDATED against a real result set.

CourseBook has no plain-GET search API. Its guided search box is entirely
AJAX-driven: the page JS (do_guided_search(), shipped in their cloudfront
bundle) POSTs to

    https://coursebook.utdallas.edu/clips/clip-cb11-hat.zog
    action=search
    s[]=term_<term>      e.g. s[]=term_26f
    s[]=<free text>       e.g. s[]=cs3345.004

using whatever session cookie (PTGSESSID) was issued by an initial GET to
/guidedsearch. That is what SEARCH_ENDPOINT/_build_session() below replicate.

In manual testing with a plain HTTP client (curl + requests-equivalent
headers, cookies, and Referer), this endpoint returned HTTP 404 even though
it is the exact call the real site's browser JS makes. Their own JS has a
fallback error message ("Search Error. Please login with your NetID to
improve access level."), which suggests anonymous/non-browser requests may
be rejected outright by something the JS can't detect either. This needs to
be re-validated by opening the browser DevTools Network tab on
coursebook.utdallas.edu, running a real guided search, and diffing the
actual request (headers, cookies, exact payload) against what's implemented
here — before relying on this module. If the direct HTTP approach turns out
to be permanently blocked, the fallback is a headless-browser fetch
(Playwright) instead of `requests`.
"""

import re
from datetime import datetime, date, time as dtime, timezone
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from services import preferences_service
from models import CourseSection

COURSEBOOK_BASE = "https://coursebook.utdallas.edu"
SEARCH_ENDPOINT = f"{COURSEBOOK_BASE}/clips/clip-cb11-hat.zog"

_WEEKDAY_LETTERS = ["M", "T", "W", "Th", "F", "S", "Su"]
# Python's Monday=0 ... Sunday=6, mapped to CourseBook-style day letters.
_PY_WEEKDAY_TO_LETTER = {0: "M", 1: "T", 2: "W", 3: "Th", 4: "F", 5: "S", 6: "Su"}


def _build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    })
    # Establish PTGSESSID cookie before the AJAX call, same as a real page load.
    session.get(f"{COURSEBOOK_BASE}/guidedsearch", timeout=15)
    return session


def _fetch_section_html(term: str, course_code: str, section: str) -> str:
    session = _build_session()
    query = f"{course_code}{section and '.' + section or ''}"
    resp = session.post(
        SEARCH_ENDPOINT,
        data={
            "action": "search",
            "s[]": [f"term_{term}", query],
        },
        headers={
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{COURSEBOOK_BASE}/guidedsearch",
            "Origin": COURSEBOOK_BASE,
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.text


def _parse_section_html(html: str, course_code: str, section: str) -> dict:
    """
    Best-effort parse of a CourseBook result fragment for one section.
    Selectors are guesses based on CourseBook's general table-row layout and
    WILL likely need adjusting once run against a real captured response.
    """
    soup = BeautifulSoup(html, "html.parser")

    row = soup.find(attrs={"class": re.compile("course-row|result-row|clsrow", re.I)})
    text_blob = row.get_text(" ", strip=True) if row else soup.get_text(" ", strip=True)

    title = None
    title_el = soup.find(attrs={"class": re.compile("course-title|cls-title", re.I)})
    if title_el:
        title = title_el.get_text(strip=True)

    instructor = None
    instr_el = soup.find(attrs={"class": re.compile("instructor", re.I)})
    if instr_el:
        instructor = instr_el.get_text(strip=True)

    location = None
    loc_el = soup.find(attrs={"class": re.compile("location|room", re.I)})
    if loc_el:
        location = loc_el.get_text(strip=True)

    # Days/time typically render like "MW 10:00 am - 11:15 am".
    days = None
    start_time = None
    end_time = None
    m = re.search(
        r"\b((?:M|T|W|Th|F|S|Su)+)\s+(\d{1,2}:\d{2}\s?[ap]m)\s*-\s*(\d{1,2}:\d{2}\s?[ap]m)",
        text_blob,
        re.I,
    )
    if m:
        days, start_time, end_time = m.group(1), m.group(2), m.group(3)

    return {
        "course_title": title,
        "instructor": instructor,
        "days": days,
        "start_time": start_time,
        "end_time": end_time,
        "location": location,
        "raw_payload": {"course_code": course_code, "section": section, "text": text_blob[:2000]},
    }


def add_or_update_course(db: Session, term: str, course_code: str, section: str) -> CourseSection:
    course_code = course_code.lower().strip()
    section = section.strip()

    html = _fetch_section_html(term, course_code, section)
    parsed = _parse_section_html(html, course_code, section)

    row = (
        db.query(CourseSection)
        .filter(
            CourseSection.term == term,
            CourseSection.course_code == course_code,
            CourseSection.section == section,
        )
        .first()
    )
    if row is None:
        row = CourseSection(term=term, course_code=course_code, section=section)
        db.add(row)

    row.course_title = parsed["course_title"]
    row.instructor = parsed["instructor"]
    row.days = parsed["days"]
    row.start_time = parsed["start_time"]
    row.end_time = parsed["end_time"]
    row.location = parsed["location"]
    row.raw_payload = parsed["raw_payload"]
    row.synced_at = datetime.utcnow()

    db.commit()
    db.refresh(row)
    return row


def get_all_courses(db: Session) -> list[CourseSection]:
    return db.query(CourseSection).order_by(CourseSection.course_code, CourseSection.section).all()


def create_manual_course(db: Session, **fields) -> CourseSection:
    """
    Adds/updates a course section with user-supplied data instead of a
    CourseBook lookup. Primary path for now, since the CourseBook scraper
    is unvalidated (see module docstring).
    """
    term = fields["term"]
    course_code = fields["course_code"].lower().strip()
    section = fields["section"].strip()

    row = (
        db.query(CourseSection)
        .filter(CourseSection.term == term, CourseSection.course_code == course_code, CourseSection.section == section)
        .first()
    )
    if row is None:
        row = CourseSection(term=term, course_code=course_code, section=section)
        db.add(row)

    for key in ("course_title", "instructor", "days", "start_time", "end_time", "location"):
        value = fields.get(key)
        if value is not None:
            setattr(row, key, value)
    row.synced_at = datetime.utcnow()

    db.commit()
    db.refresh(row)
    return row


def update_course(db: Session, course_id: str, **fields) -> CourseSection | None:
    row = db.query(CourseSection).filter(CourseSection.id == course_id).first()
    if row is None:
        return None
    for key, value in fields.items():
        if value is not None:
            setattr(row, key, value)
    row.synced_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return row


def delete_course(db: Session, course_id: str) -> bool:
    row = db.query(CourseSection).filter(CourseSection.id == course_id).first()
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True


def _parse_clock_time(value: str) -> dtime | None:
    """Parses strings like '10:00 am' / '1:15 PM' into a time object."""
    if not value:
        return None
    value = value.strip().lower().replace(" ", "")
    for fmt in ("%I:%M%p", "%H:%M"):
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            continue
    return None


def get_next_class(db: Session) -> CourseSection | None:
    """
    Returns the soonest class that is either currently in progress or still
    upcoming today, based on real time-of-day comparison (not just day-letter
    matching). Returns None if no class today is still upcoming/in-progress.

    "Today" and "now" are computed in the user's local timezone (preferences
    key "timezone", default America/Chicago for UTD), not the container's
    clock — the backend container runs on UTC, so a naive datetime.now()
    would silently pick the wrong weekday in the evening.
    """
    tz_name = preferences_service.get_preference(db, "timezone") or "America/Chicago"
    now = datetime.now(ZoneInfo(tz_name))
    today_letter = _PY_WEEKDAY_TO_LETTER[now.weekday()]

    candidates = []
    for course in db.query(CourseSection).all():
        if not course.days or not course.end_time:
            continue
        # Guard against "T" matching inside "Th" for Tuesday/Thursday.
        day_tokens = re.findall(r"Th|Su|M|T|W|F|S", course.days)
        if today_letter not in day_tokens:
            continue
        end_t = _parse_clock_time(course.end_time)
        if end_t is None or end_t < now.time():
            continue
        start_t = _parse_clock_time(course.start_time) or end_t
        candidates.append((start_t, course))

    if not candidates:
        return None

    candidates.sort(key=lambda pair: pair[0])
    return candidates[0][1]
