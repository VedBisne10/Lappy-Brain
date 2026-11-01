
import httpx

from backend.config import settings
from backend.core.exceptions import LLMConnectionError


class OllamaClient:
    def __init__(self):
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model = settings.ollama_model
        self.timeout = 300.0

    async def _send_chat_request(self, payload: dict) -> dict:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                )
                response.raise_for_status()

            return response.json()

        except httpx.HTTPStatusError as exc:
            raise LLMConnectionError(
                f"Ollama returned HTTP {exc.response.status_code}: "
                f"{exc.response.text}"
            ) from exc

        except (httpx.RequestError, ValueError) as exc:
            raise LLMConnectionError(
                "Could not communicate with Ollama. "
                "Check whether the Ollama server is running."
            ) from exc

    async def generate_response(self, prompt: str) -> str:
        if not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "stream": False,
        }

        data = await self._send_chat_request(payload)

        content = data.get("message", {}).get("content", "")

        if not isinstance(content, str) or not content.strip():
            raise LLMConnectionError(
                "Ollama returned an empty response."
            )

        return content.strip()

    async def generate_with_tools(
        self,
        messages: list,
        tools: list,
    ) -> dict:

        payload = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "stream": False,
        }

        data = await self._send_chat_request(payload)

        message = data.get("message", {})

        return {
            "content": message.get("content", ""),
            "tool_calls": message.get("tool_calls", []),
            "model": data.get("model", self.model),
            "done": data.get("done", False),
        }


ollama_client = OllamaClient()
