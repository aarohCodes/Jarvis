import json
from datetime import datetime

from sqlalchemy.orm import Session

from chat.chat_tools import TOOL_SPECS, execute_tool
from chat.llm_provider import get_llm_provider
from models import ChatMessage

MAX_TOOL_ITERATIONS = 5

SYSTEM_PROMPT = (
    "You are Jarvis, a personal assistant for a UT Dallas student. Use the "
    "available tools to answer questions about their class schedule, "
    "assignments, tasks, reminders, syllabi, and weather. Be concise. "
    "When a tool call fails or returns an error, explain the problem to "
    "the user plainly instead of guessing."
)


def _save_turn(db: Session, session_id: str, role: str, content: str | None = None, tool_calls: list | None = None, tool_call_id: str | None = None, tool_name: str | None = None) -> ChatMessage:
    message = ChatMessage(
        session_id=session_id,
        role=role,
        content=content,
        tool_calls=tool_calls,
        tool_call_id=tool_call_id,
        tool_name=tool_name,
        created_at=datetime.utcnow(),
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def _load_turns(db: Session, session_id: str, limit: int = 40) -> list[dict]:
    # Most recent `limit` turns, re-sorted back to chronological order —
    # ordering ascending with a limit would instead keep the OLDEST turns
    # forever once a conversation passes `limit` messages.
    rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
        .all()
    )
    rows.reverse()
    return [
        {
            "role": row.role,
            "content": row.content,
            "tool_calls": row.tool_calls,
            "tool_call_id": row.tool_call_id,
            "tool_name": row.tool_name,
        }
        for row in rows
    ]


def get_history(db: Session, session_id: str) -> list[ChatMessage]:
    return db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at).all()


def send_message(db: Session, session_id: str, user_message: str) -> str:
    provider = get_llm_provider()  # raises RuntimeError if unconfigured; caller turns this into a 4xx/5xx

    _save_turn(db, session_id, role="user", content=user_message)

    for _ in range(MAX_TOOL_ITERATIONS):
        turns = _load_turns(db, session_id)
        response = provider.chat(turns, TOOL_SPECS, SYSTEM_PROMPT)

        tool_calls_payload = (
            [
                {"id": tc.id, "name": tc.name, "arguments": tc.arguments, "thought_signature": tc.thought_signature}
                for tc in response.tool_calls
            ]
            if response.tool_calls
            else None
        )
        _save_turn(db, session_id, role="assistant", content=response.text, tool_calls=tool_calls_payload)

        if not response.tool_calls:
            return response.text or ""

        for tool_call in response.tool_calls:
            result = execute_tool(db, tool_call.name, tool_call.arguments)
            _save_turn(
                db,
                session_id,
                role="tool",
                content=json.dumps(result, default=str),
                tool_call_id=tool_call.id,
                tool_name=tool_call.name,
            )

    return "I wasn't able to finish that after several tool calls — try rephrasing or breaking it into a simpler question."
