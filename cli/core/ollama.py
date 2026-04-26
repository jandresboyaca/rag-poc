"""Ollama chat client with MCP-compatible tool calling.

The CLI's chat loop expects a provider that:
  - accepts a list of MCP tools and forwards them to the model,
  - returns a message with `stop_reason == "tool_use"` and content blocks of
    type ``tool_use`` (with ``id``, ``name``, ``input``) when the model
    decides to invoke a tool,
  - persists assistant tool calls + user tool results across turns.

Ollama's ``/api/chat`` endpoint supports tool calling for tool-capable models
(e.g. llama3.1, qwen2.5, qwen3, mistral-nemo). Older or chat-only models
will simply not emit ``tool_calls``; the wiring is correct either way.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass
class OllamaContentBlock:
    type: str = "text"               # "text" | "tool_use"
    text: str = ""
    id: str = ""                     # for tool_use
    name: str = ""                   # for tool_use
    input: dict = field(default_factory=dict)  # for tool_use


@dataclass
class OllamaMessage:
    content: list = field(default_factory=list)
    stop_reason: str = "end_turn"   # "end_turn" | "tool_use"

    def __post_init__(self):
        if self.content and isinstance(self.content, str):
            self.content = [OllamaContentBlock(type="text", text=self.content)]


def _to_ollama_tools(tools: list[dict] | None) -> list[dict]:
    """Translate MCP tool descriptors → Ollama tool payload (OpenAI-compatible)."""
    if not tools:
        return []
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("input_schema", {"type": "object"}),
            },
        }
        for t in tools
    ]


class Ollama:
    def __init__(self, model: str, base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url

    def add_user_message(self, messages: list, message):
        """Append a user turn. Handles plain strings, OllamaMessage, and
        the tool_result block list emitted by ToolManager."""
        if isinstance(message, OllamaMessage):
            text = self.text_from_message(message)
            messages.append({"role": "user", "content": text})
            return

        if isinstance(message, list):
            # Tool results: list of {"type": "tool_result", "tool_use_id", "content"}
            for block in message:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": block.get("tool_use_id", ""),
                            "content": block.get("content", ""),
                        }
                    )
                else:
                    messages.append({"role": "user", "content": str(block)})
            return

        messages.append({"role": "user", "content": message})

    def add_assistant_message(self, messages: list, message):
        """Append an assistant turn, including tool_calls so the next turn ties together."""
        if isinstance(message, OllamaMessage):
            text_parts = [b.text for b in message.content if b.type == "text"]
            tool_calls = [
                {
                    "id": b.id,
                    "type": "function",
                    "function": {"name": b.name, "arguments": b.input},
                }
                for b in message.content
                if b.type == "tool_use"
            ]
            entry: dict[str, Any] = {
                "role": "assistant",
                "content": "\n".join(text_parts),
            }
            if tool_calls:
                entry["tool_calls"] = tool_calls
            messages.append(entry)
            return

        if isinstance(message, list):
            messages.append({"role": "assistant", "content": str(message)})
            return

        messages.append({"role": "assistant", "content": message})

    def text_from_message(self, message: OllamaMessage) -> str:
        return "\n".join(b.text for b in message.content if b.type == "text")

    def chat(
        self,
        messages,
        system=None,
        temperature=1.0,
        stop_sequences=[],
        tools=None,
        thinking=False,
        thinking_budget=1024,
    ) -> OllamaMessage:
        ollama_messages: list[dict[str, Any]] = []
        if system:
            ollama_messages.append({"role": "system", "content": system})

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # Tool result messages — pass through as-is (already in Ollama shape).
            if role == "tool":
                ollama_messages.append(msg)
                continue

            # Assistant turns may carry tool_calls — preserve them.
            if role == "assistant" and msg.get("tool_calls"):
                ollama_messages.append(msg)
                continue

            if isinstance(content, list):
                text = "\n".join(
                    block.get("text", "") if isinstance(block, dict)
                    else getattr(block, "text", "")
                    for block in content
                    if (
                        block.get("type") == "text" if isinstance(block, dict)
                        else getattr(block, "type", "") == "text"
                    )
                )
            else:
                text = str(content)
            ollama_messages.append({"role": role, "content": text})

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": ollama_messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        ollama_tools = _to_ollama_tools(tools)
        if ollama_tools:
            payload["tools"] = ollama_tools

        response = httpx.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=300.0,
        )
        response.raise_for_status()
        data = response.json()

        msg = data.get("message", {}) or {}
        text = msg.get("content", "") or ""
        tool_calls = msg.get("tool_calls") or []

        blocks: list[OllamaContentBlock] = []
        if text:
            blocks.append(OllamaContentBlock(type="text", text=text))

        for call in tool_calls:
            fn = call.get("function", {}) or {}
            args = fn.get("arguments", {})
            # Some Ollama builds return arguments as a JSON string instead of an object.
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {"_raw": args}
            blocks.append(
                OllamaContentBlock(
                    type="tool_use",
                    id=call.get("id") or f"call_{uuid.uuid4().hex[:12]}",
                    name=fn.get("name", ""),
                    input=args or {},
                )
            )

        stop_reason = "tool_use" if tool_calls else "end_turn"
        return OllamaMessage(content=blocks, stop_reason=stop_reason)
