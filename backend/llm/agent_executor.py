
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
the available tools to complete tasks on the user's computer.

GENERAL RULES:
1. Use tools whenever a task requires filesystem information or action.
2. Never claim an operation succeeded unless its tool result confirms success.
3. Use the exact arguments required by each tool.
4. Never invent file paths, folder names, or execution results.
5. Never bypass filesystem permissions.
6. Never claim to have executed an operation you did not execute.
7. Explain the actual result after completing the task.

FILE SEARCH AND READING WORKFLOW:
1. When searching for a file, use search_filesystem with a specific filename.
2. Do not repeatedly search for the same file using the same query.
3. You may perform a second, more specific search if the first search
   does not find a suitable result.
4. If search_filesystem returns the exact file, use its returned path.
5. If the user asks to read or understand a file, call read_file
   using the exact path returned by search_filesystem.
6. Do not call search_filesystem again when you already have the
   exact path needed to read the file.
7. After read_file succeeds, use its content to answer the user.
8. If multiple matching files exist, ask the user to clarify when
   you cannot confidently identify the intended file.
9. Never invent a path to call read_file.

TOOL EXECUTION:
1. Read the results returned by every tool before choosing the next action.
2. Do not repeat an identical tool call.
3. Do not call list_directory if the search results already provide
   the exact file path required.
4. Do not perform unrelated operations.
5. If a tool fails, explain the failure instead of pretending it succeeded.

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
