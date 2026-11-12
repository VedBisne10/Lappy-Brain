import json
from typing import Any

from backend.llm.ollama_client import ollama_client
from backend.llm.tool_registry import (
    TOOL_DEFINITIONS,
    tool_registry,
)

from backend.llm.prompt_template import PROMPT_TEMPLATE

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
                "content": PROMPT_TEMPLATE,
            },
            {
                "role": "user",
                "content": user_message.strip(),
            },
        ]

        execution_history = []
        executed_calls = set()
        search_call_count = 0

        for round_number in range(1, self.max_tool_rounds + 1):

            response = await ollama_client.generate_with_tools(
                messages=messages,
                tools=TOOL_DEFINITIONS,
            )

            tool_calls = response.get("tool_calls", [])
            content = response.get("content", "")

            # The model has finished its work.
            if not tool_calls:
                return {
                    "success": True,
                    "reply": content.strip(),
                    "model": response.get("model"),
                    "tool_calls_executed": len(execution_history),
                    "execution_history": execution_history,
                }

            # Preserve the assistant's tool-call message.
            messages.append({
                "role": "assistant",
                "content": content or "",
                "tool_calls": tool_calls,
            })

            for tool_call in tool_calls:

                function_data = tool_call.get("function", {})

                tool_name = function_data.get("name")
                raw_arguments = function_data.get("arguments", {})

                if not isinstance(tool_name, str) or not tool_name:
                    tool_name = "unknown"
                    tool_result = {
                        "success": False,
                        "error": "The model returned an invalid tool name.",
                    }

                else:
                    try:
                        arguments = self._parse_arguments(raw_arguments)

                        # Create a consistent identifier for this call.
                        call_signature = (
                            tool_name,
                            json.dumps(
                                arguments,
                                sort_keys=True,
                                ensure_ascii=False,
                            ),
                        )

                        # Prevent identical tool calls from repeating.
                        if call_signature in executed_calls:
                            tool_result = {
                                "success": False,
                                "tool": tool_name,
                                "error": (
                                    "This exact tool call was already executed. "
                                    "Use its previous result instead of "
                                    "repeating the operation."
                                ),
                            }

                        # Allow at most two searches per instruction.
                        elif tool_name == "search_filesystem" and search_call_count >= 2:
                            tool_result = {
                                "success": False,
                                "tool": tool_name,
                                "error": (
                                    "The search limit for this instruction "
                                    "has been reached. Use the previous "
                                    "search results or ask the user for "
                                    "a more specific filename."
                                ),
                            }

                        else:
                            executed_calls.add(call_signature)

                            if tool_name == "search_filesystem":
                                search_call_count += 1

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
