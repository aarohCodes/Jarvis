import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Text, Boolean, DateTime, Integer, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()


def gen_uuid():
    return str(uuid.uuid4())


class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    title = Column(String(255), nullable=False)
    notes = Column(Text, nullable=True)
    due_at = Column(DateTime(timezone=True), nullable=True)
    priority = Column(String(20), default="normal")
    status = Column(String(20), default="open")
    source = Column(String(50), default="manual")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    text = Column(String(500), nullable=False)
    remind_at = Column(DateTime(timezone=True), nullable=False)
    recurrence_rule = Column(String(255), nullable=True)
    delivery_channel = Column(String(50), default="push")
    status = Column(String(20), default="pending")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    fired_at = Column(DateTime(timezone=True), nullable=True)


class CourseSection(Base):
    """Replaces calendar_cache for class schedule data, sourced from CourseBook."""
    __tablename__ = "course_sections"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    term = Column(String(10), nullable=False)          # e.g. "26f"
    course_code = Column(String(20), nullable=False)   # e.g. "cs3345"
    section = Column(String(10), nullable=False)        # e.g. "004"
    course_title = Column(String(255), nullable=True)
    instructor = Column(String(255), nullable=True)
    days = Column(String(50), nullable=True)            # e.g. "MW", "TTh"
    start_time = Column(String(20), nullable=True)       # e.g. "10:00 am"
    end_time = Column(String(20), nullable=True)
    location = Column(String(255), nullable=True)
    raw_payload = Column(JSON, nullable=True)
    synced_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class AssignmentCache(Base):
    __tablename__ = "assignments_cache"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    canvas_uid = Column(String(255), unique=True, nullable=False)
    course_name = Column(String(255), nullable=True)
    title = Column(String(500), nullable=False)
    due_at = Column(DateTime(timezone=True), nullable=True)
    description = Column(Text, nullable=True)
    html_url = Column(String(1000), nullable=True)
    synced_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class Syllabus(Base):
    __tablename__ = "syllabi"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    course_code = Column(String(20), nullable=False)   # e.g. "cs3345"
    file_name = Column(String(255), nullable=True)
    raw_text = Column(Text, nullable=False)
    uploaded_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class Preference(Base):
    __tablename__ = "preferences"

    key = Column(String(100), primary_key=True)
    value = Column(JSON, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    session_id = Column(String(100), nullable=False, default="default")
    role = Column(String(20), nullable=False)  # user | assistant | tool
    content = Column(Text, nullable=True)
    tool_calls = Column(JSON, nullable=True)   # [{id, name, arguments}], set on assistant turns that call tools
    tool_call_id = Column(String(100), nullable=True)
    tool_name = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class ActionLog(Base):
    __tablename__ = "action_log"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    action_type = Column(String(100), nullable=False)
    tool_name = Column(String(100), nullable=True)
    input_payload = Column(JSON, nullable=True)
    output_payload = Column(JSON, nullable=True)
    status = Column(String(20), default="success")
    requested_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)