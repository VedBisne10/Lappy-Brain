import json
from typing import Any

from backend.llm.ollama_client import ollama_client
from backend.llm.tool_registry import (
    TOOL_DEFINITIONS,
    tool_registry,
)


SYSTEM_PROMPT = """
You are LappyBrain, a personal AI computer assistant.

Your responsibility is to understand user instructions and use
the available tools to complete tasks on their computer.

RULES:
1. Use tools whenever a task requires filesystem information or action.
2. Never claim an operation succeeded unless its tool result confirms success.
3. Use the exact arguments required by each tool.
4. If a search returns no results, clearly report that.
5. Do not invent file paths, folder names, or execution results.
6. If information is missing, ask the user instead of guessing.
7. Never attempt to bypass filesystem permissions.
8. Do not claim to have executed operations that you did not execute.
9. Explain the actual result after completing the requested task.

You have access only to the tools explicitly provided to you.
"""


class AgentExecutor:
    """Coordinate LLM reasoning and registered tool execution."""

    def __init__(self, max_tool_rounds: int = 5):
        self.max_tool_rounds = max_tool_rounds

    @staticmethod
    def _parse_arguments(arguments: Any) -> dict:
        """Normalize and validate model-generated tool arguments."""

        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    "The model returned invalid JSON tool arguments."
                ) from exc

        if not isinstance(arguments, dict):
            raise ValueError("Tool arguments must be a JSON object.")

        return arguments

    async def execute(self, user_message: str) -> dict:
        """Process a user instruction and execute requested tools."""

        if not isinstance(user_message, str) or not user_message.strip():
            raise ValueError("User message cannot be empty.")

        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": user_message.strip(),
            },
        ]

        execution_history = []

        for round_number in range(1, self.max_tool_rounds + 1):

            # Ask Qwen to respond or request a tool.
            response = await ollama_client.generate_with_tools(
                messages=messages,
                tools=TOOL_DEFINITIONS,
            )

            tool_calls = response.get("tool_calls", [])
            content = response.get("content", "")

            # No more tool calls means the model has finished.
            if not tool_calls:
                return {
                    "success": True,
                    "reply": content.strip(),
                    "model": response.get("model"),
                    "tool_calls_executed": len(execution_history),
                    "execution_history": execution_history,
                }

            # Preserve the assistant's tool-call message in conversation.
            messages.append({
                "role": "assistant",
                "content": content or "",
                "tool_calls": tool_calls,
            })

            # Execute every requested tool.
            for tool_call in tool_calls:

                function_data = tool_call.get("function", {})

                tool_name = function_data.get("name")
                raw_arguments = function_data.get("arguments", {})

                if not isinstance(tool_name, str) or not tool_name:
                    tool_result = {
                        "success": False,
                        "error": "The model returned an invalid tool name.",
                    }
                    tool_name = "unknown"

                else:
                    try:
                        arguments = self._parse_arguments(raw_arguments)

                        tool_result = tool_registry.execute(
                            tool_name=tool_name,
                            arguments=arguments,
                        )

                    except (ValueError, TypeError) as exc:
                        tool_result = {
                            "success": False,
                            "tool": tool_name,
                            "error": str(exc),
                        }

                execution_history.append({
                    "round": round_number,
                    "tool": tool_name,
                    "result": tool_result,
                })

                # Return the actual tool result to the model.
                messages.append({
                    "role": "tool",
                    "tool_name": tool_name,
                    "content": json.dumps(
                        tool_result,
                        ensure_ascii=False,
                        default=str,
                    ),
                })

        return {
            "success": False,
            "reply": (
                "The agent reached its maximum tool-execution limit. "
                "Some operations may have completed. Please inspect "
                "the execution history."
            ),
            "model": ollama_client.model,
            "tool_calls_executed": len(execution_history),
            "execution_history": execution_history,
        }


# Shared agent executor.
agent_executor = AgentExecutor()
