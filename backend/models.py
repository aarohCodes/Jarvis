import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Text, Boolean, DateTime, Integer, ForeignKey, JSON
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
    priority = Column(String(20), default="normal")        # low | normal | high
    status = Column(String(20), default="open")             # open | done | cancelled
    source = Column(String(50), default="manual")            # manual | canvas | assistant
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    text = Column(String(500), nullable=False)
    remind_at = Column(DateTime(timezone=True), nullable=False)
    recurrence_rule = Column(String(255), nullable=True)     # e.g. RFC5545 RRULE, null = one-time
    delivery_channel = Column(String(50), default="push")    # push | email | in_app
    status = Column(String(20), default="pending")           # pending | sent | failed | cancelled
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    fired_at = Column(DateTime(timezone=True), nullable=True)


class CalendarCache(Base):
    __tablename__ = "calendar_cache"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    google_event_id = Column(String(255), unique=True, nullable=False)
    calendar_id = Column(String(255), nullable=False)
    title = Column(String(500), nullable=True)
    location = Column(String(500), nullable=True)
    start_at = Column(DateTime(timezone=True), nullable=False)
    end_at = Column(DateTime(timezone=True), nullable=False)
    all_day = Column(Boolean, default=False)
    raw_payload = Column(JSON, nullable=True)
    synced_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class AssignmentCache(Base):
    __tablename__ = "assignments_cache"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    canvas_assignment_id = Column(String(255), unique=True, nullable=False)
    course_id = Column(String(255), nullable=False)
    course_name = Column(String(255), nullable=True)
    title = Column(String(500), nullable=False)
    due_at = Column(DateTime(timezone=True), nullable=True)
    points_possible = Column(Integer, nullable=True)
    submitted = Column(Boolean, default=False)
    html_url = Column(String(1000), nullable=True)
    synced_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class Preference(Base):
    __tablename__ = "preferences"

    key = Column(String(100), primary_key=True)
    value = Column(JSON, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class ActionLog(Base):
    __tablename__ = "action_log"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    action_type = Column(String(100), nullable=False)         # e.g. "create_reminder", "tesla_climate_on"
    tool_name = Column(String(100), nullable=True)
    input_payload = Column(JSON, nullable=True)
    output_payload = Column(JSON, nullable=True)
    status = Column(String(20), default="success")            # success | failed | pending_confirmation
    requested_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)