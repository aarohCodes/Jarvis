"""
Tool registry for the Stage 5 chat layer. Each tool has a provider-agnostic
JSON-schema spec (TOOL_SPECS, sent to whichever LLM provider is active) and
a handler that executes against the real services and returns a
JSON-serializable dict for the LLM to read back.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from services import briefing_service
from services import canvas_ical
from services import course_schedule
from services import reminders_service
from services import syllabus_service
from services import tasks_service
from services import weather_service


def _iso(dt) -> str | None:
    return dt.isoformat() if dt else None


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _handle_get_next_class(db: Session, **_):
    row = course_schedule.get_next_class(db)
    if row is None:
        return {"result": "No upcoming class found for today."}
    return {
        "course_code": row.course_code,
        "title": row.course_title,
        "start_time": row.start_time,
        "end_time": row.end_time,
        "location": row.location,
    }


def _handle_get_courses_schedule(db: Session, **_):
    return [
        {
            "course_code": c.course_code,
            "section": c.section,
            "title": c.course_title,
            "days": c.days,
            "start_time": c.start_time,
            "end_time": c.end_time,
            "location": c.location,
        }
        for c in course_schedule.get_all_courses(db)
    ]


def _handle_get_assignments_due_this_week(db: Session, **_):
    return [
        {"title": a.title, "course": a.course_name, "due_at": _iso(a.due_at)}
        for a in canvas_ical.get_due_this_week(db)
    ]


def _handle_get_assignments_due_today(db: Session, **_):
    return [
        {"title": a.title, "course": a.course_name, "due_at": _iso(a.due_at)}
        for a in canvas_ical.get_due_today(db)
    ]


def _handle_create_task(db: Session, title: str, notes: str | None = None, due_at: str | None = None, priority: str = "normal", **_):
    task = tasks_service.create_task(db, title, notes, _parse_dt(due_at) if due_at else None, priority, source="chat")
    return {"id": task.id, "title": task.title, "due_at": _iso(task.due_at), "status": task.status}


def _handle_list_tasks(db: Session, status: str | None = None, **_):
    return [{"id": t.id, "title": t.title, "due_at": _iso(t.due_at), "status": t.status} for t in tasks_service.list_tasks(db, status)]


def _handle_complete_task(db: Session, task_id: str, **_):
    task = tasks_service.update_task(db, task_id, status="completed")
    if task is None:
        return {"error": f"No task with id {task_id}"}
    return {"id": task.id, "title": task.title, "status": task.status}


def _handle_create_reminder(db: Session, text: str, remind_at: str, recurrence_rule: str | None = None, **_):
    reminder = reminders_service.create_reminder(db, text, _parse_dt(remind_at), recurrence_rule, delivery_channel="log")
    return {"id": reminder.id, "text": reminder.text, "remind_at": _iso(reminder.remind_at)}


def _handle_list_reminders(db: Session, status: str | None = None, **_):
    return [{"id": r.id, "text": r.text, "remind_at": _iso(r.remind_at), "status": r.status} for r in reminders_service.list_reminders(db, status)]


def _handle_ask_syllabus(db: Session, course_code: str, question: str, **_):
    raw_text = syllabus_service.get_syllabus_text(db, course_code)
    if not raw_text:
        return {"error": f"No syllabus uploaded yet for {course_code}."}
    return {"answer": syllabus_service.naive_keyword_search(raw_text, question)}


def _handle_get_weather(db: Session, **_):
    try:
        return weather_service.get_current_weather(db)
    except RuntimeError as e:
        return {"error": str(e)}


def _handle_get_morning_briefing(db: Session, **_):
    return briefing_service.get_morning_briefing(db)


TOOL_SPECS = [
    {"name": "get_next_class", "description": "Get the user's next upcoming class today, if any.", "parameters": {"type": "object", "properties": {}, "required": []}},
    {"name": "get_courses_schedule", "description": "List all of the user's stored course sections for the current term.", "parameters": {"type": "object", "properties": {}, "required": []}},
    {"name": "get_assignments_due_this_week", "description": "List Canvas assignments due in the next 7 days.", "parameters": {"type": "object", "properties": {}, "required": []}},
    {"name": "get_assignments_due_today", "description": "List Canvas assignments due today.", "parameters": {"type": "object", "properties": {}, "required": []}},
    {
        "name": "create_task", "description": "Create a new to-do task for the user.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "notes": {"type": "string"},
                "due_at": {"type": "string", "description": "ISO 8601 datetime, optional"},
                "priority": {"type": "string", "enum": ["low", "normal", "high"]},
            },
            "required": ["title"],
        },
    },
    {
        "name": "list_tasks", "description": "List the user's tasks, optionally filtered by status.",
        "parameters": {"type": "object", "properties": {"status": {"type": "string", "enum": ["open", "completed"]}}, "required": []},
    },
    {
        "name": "complete_task", "description": "Mark a task as completed by its id.",
        "parameters": {"type": "object", "properties": {"task_id": {"type": "string"}}, "required": ["task_id"]},
    },
    {
        "name": "create_reminder", "description": "Create a conversational reminder that fires at a specific time.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "remind_at": {"type": "string", "description": "ISO 8601 datetime the reminder should fire at"},
                "recurrence_rule": {"type": "string", "description": "Optional recurrence rule, free text"},
            },
            "required": ["text", "remind_at"],
        },
    },
    {
        "name": "list_reminders", "description": "List the user's reminders, optionally filtered by status.",
        "parameters": {"type": "object", "properties": {"status": {"type": "string", "enum": ["pending", "fired"]}}, "required": []},
    },
    {
        "name": "ask_syllabus", "description": "Answer a question about a course's uploaded syllabus.",
        "parameters": {"type": "object", "properties": {"course_code": {"type": "string"}, "question": {"type": "string"}}, "required": ["course_code", "question"]},
    },
    {"name": "get_weather", "description": "Get the current weather and today's high/low at the user's home location.", "parameters": {"type": "object", "properties": {}, "required": []}},
    {"name": "get_morning_briefing", "description": "Get the full morning briefing: next class, weather, assignments due today, open tasks, and pending reminders.", "parameters": {"type": "object", "properties": {}, "required": []}},
]

_HANDLERS = {
    "get_next_class": _handle_get_next_class,
    "get_courses_schedule": _handle_get_courses_schedule,
    "get_assignments_due_this_week": _handle_get_assignments_due_this_week,
    "get_assignments_due_today": _handle_get_assignments_due_today,
    "create_task": _handle_create_task,
    "list_tasks": _handle_list_tasks,
    "complete_task": _handle_complete_task,
    "create_reminder": _handle_create_reminder,
    "list_reminders": _handle_list_reminders,
    "ask_syllabus": _handle_ask_syllabus,
    "get_weather": _handle_get_weather,
    "get_morning_briefing": _handle_get_morning_briefing,
}


def execute_tool(db: Session, name: str, arguments: dict):
    handler = _HANDLERS.get(name)
    if handler is None:
        return {"error": f"Unknown tool: {name}"}
    try:
        return handler(db, **arguments)
    except Exception as e:
        return {"error": str(e)}
