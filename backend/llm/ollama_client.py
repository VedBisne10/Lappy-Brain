
import httpx

from backend.config import settings
from backend.core.exceptions import LLMConnectionError


class OllamaClient:
    """Client for communicating with a local Ollama model."""

    def __init__(self):
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model = settings.ollama_model
        self.timeout = 120.0

    async def generate_response(self, prompt: str) -> str:
        """Generate a response from the configured local model."""

        if not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout
            ) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                )
                response.raise_for_status()

            data = response.json()
            content = data.get("message", {}).get("content", "")

            if not isinstance(content, str) or not content.strip():
                raise LLMConnectionError(
                    "Ollama returned an empty response."
                )

            return content.strip()

        except httpx.HTTPStatusError as exc:
            raise LLMConnectionError(
                f"Ollama returned HTTP {exc.response.status_code}."
            ) from exc

        except (httpx.RequestError, ValueError) as exc:
            raise LLMConnectionError(
                "Could not communicate with Ollama. "
                "Check that Ollama is running and the model is available."
            ) from exc


ollama_client = OllamaClient()
