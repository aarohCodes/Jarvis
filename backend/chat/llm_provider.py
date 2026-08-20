"""
Provider-agnostic LLM abstraction for the Stage 5 chat/tool-calling layer.

Select a provider via environment variables (neither is wired to a real key
yet — set these once an account/key exists):

    LLM_PROVIDER=claude   uses ANTHROPIC_API_KEY, optional LLM_MODEL override
                          (default: claude-haiku-4-5-20251001)
    LLM_PROVIDER=openai   uses OPENAI_API_KEY, optional LLM_MODEL override
                          (default: gpt-4o-mini)

Claude and OpenAI represent tool-calling turns very differently (content
blocks with tool_use/tool_result vs. a tool_calls array + role="tool"
messages), so conversation history is stored in a provider-agnostic "turn"
shape (see chat_service.py / models.ChatMessage) and each provider class is
responsible for translating that shape to and from its native wire format.

get_llm_provider() only raises if no provider/key is configured AND it's
actually invoked — importing this module never requires a key, so the rest
of the app boots fine with no LLM configured.
"""

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    text: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)


class LLMProvider(ABC):
    @abstractmethod
    def chat(self, turns: list[dict], tool_specs: list[dict], system: str) -> LLMResponse:
        ...


class ClaudeProvider(LLMProvider):
    def __init__(self, api_key: str, model: str):
        from anthropic import Anthropic
        self._client = Anthropic(api_key=api_key)
        self._model = model

    def _to_claude_messages(self, turns: list[dict]) -> list[dict]:
        messages = []
        pending_tool_results = []

        def flush_tool_results():
            if pending_tool_results:
                messages.append({"role": "user", "content": list(pending_tool_results)})
                pending_tool_results.clear()

        for turn in turns:
            if turn["role"] == "user":
                flush_tool_results()
                messages.append({"role": "user", "content": turn["content"]})
            elif turn["role"] == "assistant":
                flush_tool_results()
                content = []
                if turn.get("content"):
                    content.append({"type": "text", "text": turn["content"]})
                for tc in turn.get("tool_calls") or []:
                    content.append({"type": "tool_use", "id": tc["id"], "name": tc["name"], "input": tc["arguments"]})
                messages.append({"role": "assistant", "content": content})
            elif turn["role"] == "tool":
                pending_tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": turn["tool_call_id"],
                    "content": turn["content"] or "",
                })
        flush_tool_results()
        return messages

    def chat(self, turns: list[dict], tool_specs: list[dict], system: str) -> LLMResponse:
        claude_tools = [
            {"name": t["name"], "description": t["description"], "input_schema": t["parameters"]}
            for t in tool_specs
        ]
        response = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=system,
            messages=self._to_claude_messages(turns),
            tools=claude_tools,
        )
        text_parts = []
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(id=block.id, name=block.name, arguments=block.input))
        return LLMResponse(text="\n".join(text_parts) or None, tool_calls=tool_calls)


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str):
        from openai import OpenAI
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def _to_openai_messages(self, turns: list[dict], system: str) -> list[dict]:
        messages = [{"role": "system", "content": system}]
        for turn in turns:
            if turn["role"] == "user":
                messages.append({"role": "user", "content": turn["content"]})
            elif turn["role"] == "assistant":
                message = {"role": "assistant", "content": turn.get("content")}
                if turn.get("tool_calls"):
                    message["tool_calls"] = [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {"name": tc["name"], "arguments": json.dumps(tc["arguments"])},
                        }
                        for tc in turn["tool_calls"]
                    ]
                messages.append(message)
            elif turn["role"] == "tool":
                messages.append({
                    "role": "tool",
                    "tool_call_id": turn["tool_call_id"],
                    "content": turn["content"] or "",
                })
        return messages

    def chat(self, turns: list[dict], tool_specs: list[dict], system: str) -> LLMResponse:
        openai_tools = [
            {"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["parameters"]}}
            for t in tool_specs
        ]
        response = self._client.chat.completions.create(
            model=self._model,
            messages=self._to_openai_messages(turns, system),
            tools=openai_tools,
        )
        message = response.choices[0].message
        tool_calls = [
            ToolCall(id=tc.id, name=tc.function.name, arguments=json.loads(tc.function.arguments or "{}"))
            for tc in (message.tool_calls or [])
        ]
        return LLMResponse(text=message.content, tool_calls=tool_calls)


def get_llm_provider() -> LLMProvider:
    provider_name = os.getenv("LLM_PROVIDER", "").lower().strip()

    if provider_name == "claude":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("LLM_PROVIDER=claude but ANTHROPIC_API_KEY is not set.")
        model = os.getenv("LLM_MODEL", "claude-haiku-4-5-20251001")
        return ClaudeProvider(api_key, model)

    if provider_name == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("LLM_PROVIDER=openai but OPENAI_API_KEY is not set.")
        model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        return OpenAIProvider(api_key, model)

    raise RuntimeError(
        "No LLM configured. Set LLM_PROVIDER=claude (with ANTHROPIC_API_KEY) or "
        "LLM_PROVIDER=openai (with OPENAI_API_KEY) in .env."
    )
