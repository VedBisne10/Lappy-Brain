from pathlib import Path

from typing import Any


from backend.config.settings import settings


from backend.file_manager.file_operations import (

    create_folder,

    create_file,

    rename_path,

    move_path,

    list_directory,

)


from backend.file_manager.folder_scanner import search_filesystem

from backend.file_manager.file_reader import read_text_file


# Tools exposed to the Ollama model.

TOOL_DEFINITIONS = [

    {

        "type": "function",

        "function": {

            "name": "search_filesystem",

            "description": (

                "Search the computer for files and folders by name. "

                "Use this when the user wants to find something."

            ),

            "parameters": {

                "type": "object",

                "properties": {

                    "query": {"type": "string"},

                    "max_results": {

                        "type": "integer",

                        "default": 50,

                    },

                    "search_files": {"type": "boolean"},

                    "search_folders": {"type": "boolean"},

                    "strategy": {
                        "type": "string",
                        "enum": ["bfs", "dfs"],
                    },
                    "include_dependencies": {
                        "type": "boolean",
                        "default": False,
                        "description": "Set true only when the user explicitly asks to inspect installed dependencies or environment folders.",
                    },

                },

                "required": ["query"],

            },

        },

    },

    {

        "type": "function",

        "function": {

            "name": "read_file",

            "description": (

                "Read the contents of an existing supported text or "

                "code file using its absolute path. Use this after "

                "search_filesystem when the user wants to understand "

                "or analyze a file. Do not use this for binary files."

            ),

            "parameters": {

                "type": "object",

                "properties": {

                    "file_path": {

                        "type": "string",

                        "description": "Absolute path of the file to read.",

                    },

                },

                "required": ["file_path"],

            },

        },

    },

    {

        "type": "function",

        "function": {

            "name": "list_directory",

            "description": (

                "List files and subfolders inside an existing directory."

            ),

            "parameters": {

                "type": "object",

                "properties": {

                    "directory_path": {"type": "string"},

                },

                "required": ["directory_path"],

            },

        },

    },

    {

        "type": "function",

        "function": {

            "name": "create_folder",

            "description": (

                "Create a new folder at the specified path. "

                "The parent directory must already exist."

            ),

            "parameters": {

                "type": "object",

                "properties": {

                    "folder_path": {"type": "string"},

                },

                "required": ["folder_path"],

            },

        },

    },

    {

        "type": "function",

        "function": {

            "name": "create_file",

            "description": (

                "Create a new UTF-8 text file without overwriting "

                "an existing file."

            ),

            "parameters": {

                "type": "object",

                "properties": {

                    "file_path": {"type": "string"},

                    "content": {"type": "string"},

                },

                "required": ["file_path"],

            },

        },

    },

    {

        "type": "function",

        "function": {

            "name": "rename_path",

            "description": (

                "Rename an existing file or folder without moving it "

                "to another directory."

            ),

            "parameters": {

                "type": "object",

                "properties": {

                    "source_path": {"type": "string"},

                    "new_name": {"type": "string"},

                },

                "required": ["source_path", "new_name"],

            },

        },

    },

    {

        "type": "function",

        "function": {

            "name": "move_path",

            "description": (

                "Move an existing file or folder to another directory. "

                "The destination must not already exist."

            ),

            "parameters": {

                "type": "object",

                "properties": {

                    "source_path": {"type": "string"},

                    "destination_path": {"type": "string"},

                },

                "required": ["source_path", "destination_path"],

            },

        },

    },

]


class ToolRegistry:

    """Validate and execute tools requested by the LLM."""


    def __init__(self):

        self.allowed_roots = settings.file_search_roots


        self._tools = {

            "search_filesystem": self._search_filesystem,

            "read_file": self._read_file,

            "list_directory": self._list_directory,

            "create_folder": self._create_folder,

            "create_file": self._create_file,

            "rename_path": self._rename_path,

            "move_path": self._move_path,

        }


    @staticmethod

    def _validate_arguments(

        arguments: dict[str, Any],

        allowed: set[str],

        required: set[str],

    ) -> None:

        """Reject unexpected or missing tool arguments."""


        if not isinstance(arguments, dict):

            raise ValueError("Tool arguments must be a JSON object.")


        unexpected = set(arguments) - allowed

        missing = required - set(arguments)


        if unexpected:

            raise ValueError(

                f"Unexpected arguments: {', '.join(sorted(unexpected))}"

            )


        if missing:

            raise ValueError(

                f"Missing arguments: {', '.join(sorted(missing))}"

            )


    @staticmethod

    def _require_string(value: Any, name: str) -> str:

        """Validate a non-empty string argument."""


        if not isinstance(value, str) or not value.strip():

            raise ValueError(f"{name} must be a non-empty string.")


        return value.strip()


    def _search_filesystem(self, arguments: dict) -> dict:

        allowed = {

            "query",

            "max_results",

            "search_files",

            "search_folders",

            "strategy",
            "include_dependencies",

        }


        self._validate_arguments(

            arguments,

            allowed,

            {"query"},

        )


        query = self._require_string(arguments["query"], "query")

        max_results = arguments.get("max_results", 50)

        search_files = arguments.get("search_files", True)

        search_folders = arguments.get("search_folders", True)

        strategy = arguments.get("strategy", "bfs")
        include_dependencies = arguments.get("include_dependencies", False)

        if not isinstance(include_dependencies, bool):
            raise ValueError("include_dependencies must be a boolean.")

        if (

            isinstance(max_results, bool)

            or not isinstance(max_results, int)

            or not 1 <= max_results <= 500

        ):

            raise ValueError("max_results must be between 1 and 500.")


        if not isinstance(search_files, bool):

            raise ValueError("search_files must be a boolean.")


        if not isinstance(search_folders, bool):

            raise ValueError("search_folders must be a boolean.")


        if not search_files and not search_folders:

            raise ValueError("At least one search type must be enabled.")


        if strategy not in {"bfs", "dfs"}:

            raise ValueError("strategy must be bfs or dfs.")


        results = search_filesystem(

            query=query,

            search_roots=settings.file_search_roots,

            max_results=max_results,

            search_files=search_files,

            search_folders=search_folders,

            strategy=strategy,
            include_dependencies=include_dependencies,

        )


        return {

            "result_count": len(results),

            "results": results,

        }


    def _read_file(self, arguments: dict) -> dict:

        """Read a supported file inside an authorized drive."""


        self._validate_arguments(

            arguments,

            {"file_path"},

            {"file_path"},

        )


        file_path = Path(

            self._require_string(arguments["file_path"], "file_path")

        )


        if not file_path.is_absolute():

            raise ValueError("An absolute file path is required.")


        # Resolve the path and verify that it belongs to an

        # authorized root before passing it to the file reader.

        resolved_path = file_path.resolve(strict=True)


        allowed_root = None


        for root in settings.file_search_roots:

            resolved_root = Path(root).resolve()


            try:

                resolved_path.relative_to(resolved_root)

                allowed_root = resolved_root

                break

            except ValueError:

                continue


        if allowed_root is None:

            raise PermissionError(

                "The requested file is outside authorized locations."

            )


        if not resolved_path.is_file():

            raise ValueError("The requested path is not a file.")


        content = read_text_file(

            file_path=str(resolved_path),

            allowed_root=str(allowed_root),

        )


        if not isinstance(content, str):

            raise ValueError("The file reader returned invalid content.")


        return {

            "file_path": str(resolved_path),

            "content": content,

            "character_count": len(content),

        }


    def _list_directory(self, arguments: dict) -> dict:

        self._validate_arguments(

            arguments,

            {"directory_path"},

            {"directory_path"},

        )


        return list_directory(

            directory_path=self._require_string(

                arguments["directory_path"], "directory_path"

            ),

            allowed_roots=settings.file_search_roots,

        )


    def _create_folder(self, arguments: dict) -> dict:

        self._validate_arguments(

            arguments,

            {"folder_path"},

            {"folder_path"},

        )


        return create_folder(

            folder_path=self._require_string(

                arguments["folder_path"], "folder_path"

            ),

            allowed_roots=settings.file_search_roots,

        )


    def _create_file(self, arguments: dict) -> dict:

        self._validate_arguments(

            arguments,

            {"file_path", "content"},

            {"file_path"},

        )


        content = arguments.get("content", "")


        if not isinstance(content, str):

            raise ValueError("content must be a string.")


        if len(content.encode("utf-8")) > 5 * 1024 * 1024:

            raise ValueError("File content cannot exceed 5 MB.")


        return create_file(

            file_path=self._require_string(

                arguments["file_path"], "file_path"

            ),

            allowed_roots=settings.file_search_roots,

            content=content,

        )


    def _rename_path(self, arguments: dict) -> dict:

        self._validate_arguments(

            arguments,

            {"source_path", "new_name"},

            {"source_path", "new_name"},

        )


        return rename_path(

            source_path=self._require_string(

                arguments["source_path"], "source_path"

            ),

            new_name=self._require_string(

                arguments["new_name"], "new_name"

            ),

            allowed_roots=settings.file_search_roots,

        )


    def _move_path(self, arguments: dict) -> dict:

        self._validate_arguments(

            arguments,

            {"source_path", "destination_path"},

            {"source_path", "destination_path"},

        )


        return move_path(

            source_path=self._require_string(

                arguments["source_path"], "source_path"

            ),

            destination_path=self._require_string(

                arguments["destination_path"], "destination_path"

            ),

            allowed_roots=settings.file_search_roots,

        )


    def execute(self, tool_name: str, arguments: dict) -> dict:

        """Execute a registered tool and return its actual result."""


        tool = self._tools.get(tool_name)


        if tool is None:

            return {

                "success": False,

                "error": f"Tool '{tool_name}' is not registered.",

            }


        try:

            result = tool(arguments)


            return {

                "success": True,

                "tool": tool_name,

                "result": result,

            }


        except (ValueError, TypeError, PermissionError, OSError) as exc:

            return {

                "success": False,

                "tool": tool_name,

                "error": str(exc),

            }


# Shared registry instance.

tool_registry = ToolRegistry()
