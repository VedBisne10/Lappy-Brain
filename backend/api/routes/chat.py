from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from backend.core.exceptions import LLMConnectionError
from backend.llm import ollama_client

# All routes in this file will be under /api
router = APIRouter(prefix = "/api", tags=["Chat"])


class ChatRequest(BaseModel):
    """Validate a message submitted by the user."""

    message : str = Field(
        min_length = 1,
        max_length = 10000,
        description = "The message to send to LappyBrain.", 
    )

    @field_validator("message")
    @classmethod
    def validate_message(cls, value : str) -> str:
        # Remove leading/trailing whitespace before checking if the message is empty
        value = value.strip()

        # If the message is blank after stripping, reject it with a clear error
        if not value:
            raise ValueError("Message cannot be empty or whitespace.")

        return value


class ChatResponse(BaseModel):
    """Structure the assistant's response."""

    reply : str    # The text the AI replied with
    model : str    # The name of the model that generated the reply


@router.post(
    "/chat", 
    response_model = ChatResponse,
    status_code = status.HTTP_200_OK, 
)
async def chat(request : ChatRequest) -> ChatResponse:
    """Send a message to the local AI model and return its reply."""

    try:
        # Send the user's message to Ollama and wait for a response
        reply = await ollama_client.generate_response(
            request.message
        )

        # Package the reply and model name into the response format
        return ChatResponse(
            reply = reply,
            model = ollama_client.model,
        )
    
    except LLMConnectionError as exc:
        # If Ollama is unreachable or crashed, return a 503 "service unavailable" error
        raise HTTPException(
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE,
            detail = str(exc),
        ) from exc
