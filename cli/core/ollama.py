import httpx
from dataclasses import dataclass, field
from typing import Any


@dataclass
class OllamaContentBlock:
    type: str = "text"
    text: str = ""


@dataclass
class OllamaMessage:
    content: list = field(default_factory=list)
    stop_reason: str = "end_turn"

    def __post_init__(self):
        if self.content and isinstance(self.content, str):
            self.content = [OllamaContentBlock(type="text", text=self.content)]


class Ollama:
    def __init__(self, model: str, base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url

    def add_user_message(self, messages: list, message):
        content = message
        if isinstance(message, OllamaMessage):
            content = "\n".join(
                block.text for block in message.content if block.type == "text"
            )
        elif isinstance(message, list):
            content = str(message)
        messages.append({"role": "user", "content": content})

    def add_assistant_message(self, messages: list, message):
        content = message
        if isinstance(message, OllamaMessage):
            content = "\n".join(
                block.text for block in message.content if block.type == "text"
            )
        elif isinstance(message, list):
            content = str(message)
        messages.append({"role": "assistant", "content": content})

    def text_from_message(self, message: OllamaMessage) -> str:
        return "\n".join(
            block.text for block in message.content if block.type == "text"
        )

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
        ollama_messages = []
        if system:
            ollama_messages.append({"role": "system", "content": system})

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if isinstance(content, list):
                text = "\n".join(
                    block.get("text", "") if isinstance(block, dict) else getattr(block, "text", "")
                    for block in content
                    if (block.get("type") == "text" if isinstance(block, dict) else getattr(block, "type", "") == "text")
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

        response = httpx.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=120.0,
        )
        response.raise_for_status()
        data = response.json()

        text = data.get("message", {}).get("content", "")
        return OllamaMessage(
            content=[OllamaContentBlock(type="text", text=text)],
            stop_reason="end_turn",
        )
