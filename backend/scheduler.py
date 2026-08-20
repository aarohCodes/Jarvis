"""
Background jobs, run in-process via APScheduler rather than a separate
Celery+Redis worker — simpler to containerize and migrate to the Raspberry
Pi later, at the cost of not surviving a backend restart mid-check
(acceptable for a personal project polling every 60s).

Three jobs:
- _check_reminders: fires any due reminder (every 60s).
- _check_morning_briefing: fires once per day at the configured wake_time
  (every 5 min, self-debouncing via a "last fired date" preference).
- _sync_assignments: pulls fresh Canvas data and proactively creates
  reminders for newly-visible deadlines, instead of waiting to be asked
  (every 30 min) — the "agentic" half of this file; the other two jobs
  just react to state that's already there.

All three push a real notification via services.notification_service
(ntfy.sh) when NTFY_TOPIC is configured, in addition to the action_log/
stdout record that's always written regardless.
"""

import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler

from services import briefing_service
from services import canvas_ical
from services import notification_service
from services import preferences_service
from services import reminders_service
from database import SessionLocal
from models import ActionLog

_scheduler = BackgroundScheduler()


def _log_action(db, action_type: str, payload: dict) -> None:
    db.add(ActionLog(
        action_type=action_type,
        input_payload=payload,
        status="success",
        requested_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
    ))
    db.commit()


def _check_reminders() -> None:
    db = SessionLocal()
    try:
        for reminder in reminders_service.get_due_reminders(db):
            _log_action(db, "reminder_fired", {"reminder_id": reminder.id, "text": reminder.text})
            print(f"[REMINDER] {reminder.remind_at.isoformat()} — {reminder.text}", flush=True)
            notification_service.send_notification("Reminder", reminder.text, priority="high")
            reminders_service.mark_fired(db, reminder)
    finally:
        db.close()


def _format_briefing_summary(briefing: dict) -> str:
    parts = []

    next_class = briefing.get("next_class")
    parts.append(
        f"Next class: {next_class.get('title') or next_class.get('course_code')} at {next_class.get('start_time')}"
        if next_class else "No more classes today"
    )

    weather = briefing.get("weather")
    if weather:
        parts.append(f"{weather.get('current_temp_c')}°C, {weather.get('current_condition')}")

    due_today = briefing.get("assignments_due_today") or []
    if due_today:
        parts.append(f"{len(due_today)} assignment(s) due today")

    open_tasks = briefing.get("open_tasks") or []
    if open_tasks:
        parts.append(f"{len(open_tasks)} open task(s)")

    return " · ".join(parts)


def _check_morning_briefing() -> None:
    db = SessionLocal()
    try:
        tz_name = preferences_service.get_preference(db, "timezone") or "America/Chicago"
        wake_time = preferences_service.get_preference(db, "wake_time") or "07:00"
        try:
            hour, minute = (int(part) for part in wake_time.split(":"))
        except ValueError:
            return

        now = datetime.now(ZoneInfo(tz_name))
        today_str = now.date().isoformat()

        if preferences_service.get_preference(db, "briefing_last_fired_date") == today_str:
            return
        if now.hour != hour or not (minute <= now.minute < minute + 5):
            return

        briefing = briefing_service.get_morning_briefing(db)
        _log_action(db, "morning_briefing", briefing)
        print(f"[MORNING BRIEFING] {json.dumps(briefing, default=str)}", flush=True)
        notification_service.send_notification("Morning Briefing", _format_briefing_summary(briefing))
        preferences_service.set_preference(db, "briefing_last_fired_date", today_str)
    finally:
        db.close()


def _sync_assignments() -> None:
    if not os.getenv("CANVAS_ICAL_URL"):
        return  # not configured yet — silent no-op rather than log spam every 30 min

    db = SessionLocal()
    try:
        try:
            synced = canvas_ical.sync_assignments(db)
        except Exception as e:
            _log_action(db, "assignment_sync_failed", {"error": str(e)})
            print(f"[ASSIGNMENT SYNC] failed: {e}", flush=True)
            return

        newly_reminded = canvas_ical.create_reminders_for_upcoming_assignments(db)
        _log_action(db, "assignment_sync", {"synced": synced, "new_reminders": len(newly_reminded)})

        if newly_reminded:
            titles = ", ".join(a.title for a in newly_reminded[:5])
            more = f" (+{len(newly_reminded) - 5} more)" if len(newly_reminded) > 5 else ""
            summary = f"Added {len(newly_reminded)} reminder(s) for: {titles}{more}"
            print(f"[ASSIGNMENT SYNC] {summary}", flush=True)
            notification_service.send_notification("New assignments synced", summary)
    finally:
        db.close()


def start() -> None:
    # misfire_grace_time=None: always run a late tick rather than silently
    # skip it (APScheduler's 1-second default drops ticks whenever the
    # process is briefly busy, e.g. during a --reload restart — unacceptable
    # for reminders). coalesce=True collapses any backlog of missed ticks
    # into a single run instead of firing repeatedly to catch up.
    _scheduler.add_job(_check_reminders, "interval", seconds=60, id="check_reminders", replace_existing=True, misfire_grace_time=None, coalesce=True)
    _scheduler.add_job(_check_morning_briefing, "interval", minutes=5, id="check_morning_briefing", replace_existing=True, misfire_grace_time=None, coalesce=True)
    _scheduler.add_job(_sync_assignments, "interval", minutes=30, id="sync_assignments", replace_existing=True, misfire_grace_time=None, coalesce=True)
    _scheduler.start()


def shutdown() -> None:
    _scheduler.shutdown(wait=False)
