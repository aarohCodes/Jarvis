from sqlalchemy.orm import Session

import canvas_ical
import course_schedule
import reminders_service
import tasks_service
import weather_service


def get_morning_briefing(db: Session) -> dict:
    next_class = course_schedule.get_next_class(db)

    try:
        weather = weather_service.get_current_weather(db)
    except RuntimeError:
        weather = None

    due_today = canvas_ical.get_due_today(db)
    open_tasks = tasks_service.list_tasks(db, status="open")
    pending_reminders = reminders_service.list_reminders(db, status="pending")

    return {
        "next_class": (
            {
                "course_code": next_class.course_code,
                "title": next_class.course_title,
                "start_time": next_class.start_time,
                "end_time": next_class.end_time,
                "location": next_class.location,
            }
            if next_class
            else None
        ),
        "weather": weather,
        "assignments_due_today": [
            {"title": a.title, "course": a.course_name, "due_at": a.due_at.isoformat() if a.due_at else None}
            for a in due_today
        ],
        "open_tasks": [{"id": t.id, "title": t.title, "due_at": t.due_at.isoformat() if t.due_at else None} for t in open_tasks],
        "pending_reminders": [
            {"id": r.id, "text": r.text, "remind_at": r.remind_at.isoformat()} for r in pending_reminders
        ],
    }
