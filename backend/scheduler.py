"""
Stage 6 (reminders) + Stage 8 (morning briefing) background jobs, run
in-process via APScheduler rather than a separate Celery+Redis worker —
simpler to containerize and migrate to the Raspberry Pi later, at the cost
of not surviving a backend restart mid-check (acceptable for a personal
project polling every 60s).

Delivery is a stopgap: reminders/briefings are logged to `action_log` and
printed to the container's stdout. Swap for real push once the mobile app
exists (see project notes, Stage 6).
"""

import json
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler

import briefing_service
import preferences_service
import reminders_service
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
            reminders_service.mark_fired(db, reminder)
    finally:
        db.close()


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
        preferences_service.set_preference(db, "briefing_last_fired_date", today_str)
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
    _scheduler.start()


def shutdown() -> None:
    _scheduler.shutdown(wait=False)
