from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    title: str
    notes: Optional[str] = None
    due_at: Optional[datetime] = None
    priority: str = "normal"
    source: str = "manual"


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    notes: Optional[str] = None
    due_at: Optional[datetime] = None
    priority: Optional[str] = None
    status: Optional[str] = None


class ReminderCreate(BaseModel):
    text: str
    remind_at: datetime
    recurrence_rule: Optional[str] = None
    delivery_channel: str = "log"


class ReminderUpdate(BaseModel):
    text: Optional[str] = None
    remind_at: Optional[datetime] = None
    recurrence_rule: Optional[str] = None
    delivery_channel: Optional[str] = None
    status: Optional[str] = None


class PreferenceSet(BaseModel):
    value: Any


class CourseManualCreate(BaseModel):
    term: str
    course_code: str
    section: str
    course_title: Optional[str] = None
    instructor: Optional[str] = None
    days: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    location: Optional[str] = None


class CourseUpdate(BaseModel):
    course_title: Optional[str] = None
    instructor: Optional[str] = None
    days: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    location: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
