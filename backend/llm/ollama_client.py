import httpx

from backend.config import settings
from backend.core.exceptions import LLMConnectionError


class OllamaClient:
    """Client for communicating with a local Ollama model."""

    def __init__(self):
        # Strip any trailing slash so URL joins don't end up with double slashes
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model = settings.ollama_model
        self.timeout = 120.0   # Wait up to 2 minutes for the model to respond

    async def generate_response(self, prompt: str) -> str:
        """Send a prompt to Ollama and return the model's text reply."""

        # Reject blank or whitespace-only prompts before even hitting the network
        if not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        # Build the request body in the format Ollama's /api/chat endpoint expects
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "stream": False,   # Get the full response at once instead of a streamed chunk-by-chunk reply
        }

        try:
            # Open an async HTTP session, send the request, and wait for the response
            async with httpx.AsyncClient(
                timeout=self.timeout
            ) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                )
                # Raise an exception immediately if Ollama returned a 4xx or 5xx status code
                response.raise_for_status()

            # Pull the actual text out of the nested JSON response structure
            data = response.json()
            content = data.get("message", {}).get("content", "")

            # If the model returned nothing useful, treat that as a connection-level error
            if not isinstance(content, str) or not content.strip():
                raise LLMConnectionError(
                    "Ollama returned an empty response."
                )

            return content.strip()

        except httpx.HTTPStatusError as exc:
            # Ollama was reachable but returned an HTTP error code (e.g. 404, 500)
            raise LLMConnectionError(
                f"Ollama returned HTTP {exc.response.status_code}."
            ) from exc

        except (httpx.RequestError, ValueError) as exc:
            # Network-level failure (timeout, refused connection, DNS error, etc.)
            raise LLMConnectionError(
                "Could not communicate with Ollama. "
                "Check that Ollama is running and the model is available."
            ) from exc


# Shared client instance — import this everywhere so only one connection pool is created
ollama_client = OllamaClient()
