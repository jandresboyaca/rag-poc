import pytest
from unittest.mock import patch, MagicMock
from core.ollama import Ollama, OllamaMessage, OllamaContentBlock


class TestOllamaContentBlock:
    def test_default_values(self):
        block = OllamaContentBlock()
        assert block.type == "text"
        assert block.text == ""


class TestOllamaMessage:
    def test_default_values(self):
        msg = OllamaMessage()
        assert msg.content == []
        assert msg.stop_reason == "end_turn"

    def test_string_content_conversion(self):
        msg = OllamaMessage(content="Hello world")
        assert isinstance(msg.content, list)
        assert len(msg.content) == 1
        assert msg.content[0].text == "Hello world"

    def test_list_content_preserved(self):
        content = [OllamaContentBlock(type="text", text="test")]
        msg = OllamaMessage(content=content)
        assert msg.content == content


class TestOllama:
    def test_init_default_base_url(self):
        ollama = Ollama(model="llama2")
        assert ollama.model == "llama2"
        assert ollama.base_url == "http://localhost:11434"

    def test_init_custom_base_url(self):
        ollama = Ollama(model="llama2", base_url="http://custom:8080")
        assert ollama.base_url == "http://custom:8080"

    def test_add_user_message_string(self):
        ollama = Ollama(model="llama2")
        messages = []
        ollama.add_user_message(messages, "Hello")
        assert len(messages) == 1
        assert messages[0] == {"role": "user", "content": "Hello"}

    def test_add_user_message_ollama_message(self):
        ollama = Ollama(model="llama2")
        msg = OllamaMessage(content=[OllamaContentBlock(text="Hello"), OllamaContentBlock(text="World")])
        messages = []
        ollama.add_user_message(messages, msg)
        assert len(messages) == 1
        assert messages[0] == {"role": "user", "content": "Hello\nWorld"}

    def test_add_user_message_list(self):
        ollama = Ollama(model="llama2")
        messages = []
        ollama.add_user_message(messages, ["item1", "item2"])
        assert len(messages) == 1
        assert messages[0]["role"] == "user"

    def test_add_assistant_message_string(self):
        ollama = Ollama(model="llama2")
        messages = []
        ollama.add_assistant_message(messages, "Response")
        assert len(messages) == 1
        assert messages[0] == {"role": "assistant", "content": "Response"}

    def test_add_assistant_message_ollama_message(self):
        ollama = Ollama(model="llama2")
        msg = OllamaMessage(content=[OllamaContentBlock(text="Response text")])
        messages = []
        ollama.add_assistant_message(messages, msg)
        assert messages[0] == {"role": "assistant", "content": "Response text"}

    def test_text_from_message(self):
        ollama = Ollama(model="llama2")
        msg = OllamaMessage(content=[
            OllamaContentBlock(type="text", text="Line 1"),
            OllamaContentBlock(type="other", text="Skip"),
            OllamaContentBlock(type="text", text="Line 2"),
        ])
        result = ollama.text_from_message(msg)
        assert result == "Line 1\nLine 2"

    @patch("core.ollama.httpx.post")
    def test_chat_basic(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"message": {"content": "Test response"}}
        mock_post.return_value = mock_response

        ollama = Ollama(model="llama2")
        messages = [{"role": "user", "content": "Hello"}]
        result = ollama.chat(messages)

        assert isinstance(result, OllamaMessage)
        assert ollama.text_from_message(result) == "Test response"
        mock_post.assert_called_once()

    @patch("core.ollama.httpx.post")
    def test_chat_with_system(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"message": {"content": "Response"}}
        mock_post.return_value = mock_response

        ollama = Ollama(model="llama2")
        result = ollama.chat([], system="You are helpful")

        call_kwargs = mock_post.call_args[1]
        assert any(m["role"] == "system" and "helpful" in m["content"] for m in call_kwargs["json"]["messages"])

    @patch("core.ollama.httpx.post")
    def test_chat_with_temperature(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"message": {"content": "Response"}}
        mock_post.return_value = mock_response

        ollama = Ollama(model="llama2")
        ollama.chat([], temperature=0.7)

        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["options"]["temperature"] == 0.7
