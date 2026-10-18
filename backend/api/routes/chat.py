from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from backend.core.exceptions import LLMConnectionError
from backend.llm import ollama_client

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
        value = value.strip()

        if not value:
            raise ValueError("Message cannot be empty or whitespace.")

        return value


class ChatResponse(BaseModel):
    """Structure the assistant's response."""

    reply : str
    model : str

@router.post(
    "/chat", 
    response_model = ChatResponse,
    status_code = status.HTTP_200_OK, 
)

async def chat(request : ChatRequest) -> ChatResponse:
    """Send a message to the local AI model."""

    try:
        reply = await ollama_client.generate_response(
            request.message
        )

        return ChatResponse(
            reply = reply,
            model = ollama_client.model,
        )
    
    except LLMConnectionError as exc:
        raise HTTPException(
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE,
            detail = str(exc),
        ) from exc