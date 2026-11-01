from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.llm.agent_executor import agent_executor
from backend.core.exceptions import LLMConnectionError


router = APIRouter(
    prefix="/api/agent",
    tags=["Agent"],
)


class AgentRequest(BaseModel):
    instruction: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Natural-language instruction for LappyBrain.",
    )


class AgentResponse(BaseModel):
    success: bool
    reply: str = ""
    model: str = ""
    tool_calls_executed: int = 0
    execution_history: list[dict[str, Any]] = Field(
        default_factory=list
    )


@router.post("/execute", response_model=AgentResponse)
async def execute_agent(request: AgentRequest):
    instruction = request.instruction.strip()

    if not instruction:
        raise HTTPException(
            status_code=400,
            detail="Instruction cannot be empty.",
        )

    try:
        result = await agent_executor.execute(instruction)

        return AgentResponse(
            success=result.get("success", False),
            reply=result.get("reply", ""),
            model=result.get("model", ""),
            tool_calls_executed=result.get(
                "tool_calls_executed", 0
            ),
            execution_history=result.get(
                "execution_history", []
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except LLMConnectionError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Agent execution failed: {str(exc)}",
        ) from exc
