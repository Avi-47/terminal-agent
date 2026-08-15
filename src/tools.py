import json
import shlex
import subprocess
from pathlib import Path
ALLOWED_COMMANDS = {
    "python",
    "python.exe",
}
def validate_command(args):
    """
    Validate the parsed command before execution.
    Returns:
        None if allowed.
        Error message string if rejected.
    """
    if not args:
        return "Error: command must not be empty."
    program = Path(args[0]).name.lower()
    if program not in ALLOWED_COMMANDS:
        return f"Error: command is not allowed: {program}"
    return None

# terminal-agent/
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
def resolve_workspace_path(path):
    """
    Resolve a path relative to the agent workspace.
    Prevents file tools from escaping the workspace through
    paths such as ../../somewhere.
    """
    if not path or not path.strip():
        raise ValueError("path must not be empty")
    requested = Path(path)
    if requested.is_absolute():
        candidate = requested.resolve()
    else:
        candidate = (WORKSPACE_ROOT / requested).resolve()
    try:
        candidate.relative_to(WORKSPACE_ROOT)
    except ValueError:
        raise ValueError(
            f"path is outside the workspace: {path}"
        )
    return candidate

def read_file(path):
    try:
        file_path = resolve_workspace_path(path)
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
        if not content:
            return f"File is empty: {path}"
        return content
    except FileNotFoundError:
        return f"File not found: {path}"
    except ValueError as e:
        return f"Error: {e}"
    except OSError as e:
        return f"Error reading file '{path}': {e}"

def write_file(path, content):
    if content is None:
        return "Error: content must not be None."
    try:
        file_path = resolve_workspace_path(path)
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(content)
        return f"Successfully wrote file: {path}"
    except ValueError as e:
        return f"Error: {e}"
    except OSError as e:
        return f"Error writing file '{path}': {e}"

def list_files(path="."):
    """
    List the immediate contents of a directory inside the workspace.
    """
    try:
        directory = resolve_workspace_path(path)
        if not directory.exists():
            return f"Error: directory not found: {path}"
        if not directory.is_dir():
            return f"Error: path is not a directory: {path}"
        entries = sorted(directory.iterdir(), key=lambda item: item.name.lower())
        if not entries:
            return f"Directory is empty: {path}"
        results = []
        for entry in entries:
            if entry.is_dir():
                results.append(f"{entry.name}/")
            else:
                results.append(entry.name)
        return "\n".join(results)
    except ValueError as e:
        return f"Error: {e}"
    except OSError as e:
        return f"Error listing directory '{path}': {e}"

def search_files(query, path="."):
    """
    Search text files inside the workspace for a given string.
    Returns matching file paths and line numbers.
    """
    if not query or not query.strip():
        return "Error: search query must not be empty."
    try:
        search_root = resolve_workspace_path(path)
        if not search_root.exists():
            return f"Error: path not found: {path}"
        if not search_root.is_dir():
            return f"Error: path is not a directory: {path}"
        matches = []
        for file_path in search_root.rglob("*"):
            if not file_path.is_file():
                continue
            # Avoid searching Git internals and Python cache files.
            if ".git" in file_path.parts:
                continue
            if "__pycache__" in file_path.parts:
                continue
            try:
                with open(
                    file_path,
                    "r",
                    encoding="utf-8",
                ) as file:
                    for line_number, line in enumerate(file, start=1):
                        if query.lower() in line.lower():
                            relative_path = file_path.relative_to(
                                WORKSPACE_ROOT
                            )
                            matches.append(
                                f"{relative_path}:{line_number}: "
                                f"{line.rstrip()}"
                            )

                            if len(matches) >= 100:
                                return (
                                    "\n".join(matches)
                                    + "\n\nSearch stopped after 100 matches."
                                )
            except (UnicodeDecodeError, OSError):
                # Ignore binary/unreadable files.
                continue
        if not matches:
            return f"No matches found for: {query}"
        return "\n".join(matches)
    except ValueError as e:
        return f"Error: {e}"

def run_command(command, timeout=10):
    """
    Execute an allowed command inside the agent workspace.
    """
    if not command or not command.strip():
        return "Error: command must not be empty."
    if not isinstance(timeout, int):
        return "Error: timeout must be an integer."
    if timeout < 1 or timeout > 30:
        return "Error: timeout must be between 1 and 30 seconds."
    try:
        args = shlex.split(command, posix=True)
        if not args:
            return "Error: command must not be empty."
        validation_error = validate_command(args)
        if validation_error:
            return validation_error
        result = subprocess.run(
            args,
            cwd=WORKSPACE_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        output = [
            f"Exit code: {result.returncode}"
        ]
        if stdout:
            output.append(f"STDOUT:\n{stdout}")
        if stderr:
            output.append(f"STDERR:\n{stderr}")
        return "\n\n".join(output)
    except subprocess.TimeoutExpired:
        return (
            f"Error: command timed out after {timeout} seconds."
        )
    except FileNotFoundError:
        return f"Error: command not found: {command}"
    except OSError as e:
        return f"Error running command: {e}"

def git_status():
    """
    Return the current Git working-tree status for the workspace.
    """
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=WORKSPACE_ROOT,
            capture_output=True,
            text=True,
            shell=False,
            timeout=10,
        )
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        if result.returncode != 0:
            if stderr:
                return f"Error: git status failed:\n{stderr}"
            return (
                f"Error: git status failed with exit code "
                f"{result.returncode}."
            )
        if not stdout:
            return "Git working tree is clean."
        return stdout
    except subprocess.TimeoutExpired:
        return "Error: git status timed out."
    except FileNotFoundError:
        return "Error: git is not installed or not available on PATH."
    except OSError as e:
        return f"Error running git status: {e}"

TOOL_FUNCTIONS = {
    "read_file": read_file,
    "write_file": write_file,
    "list_files": list_files,
    "search_files": search_files,
    "run_command": run_command,
    "git_status": git_status,
}

TOOLS = [
    {
        "type": "function",
        "name": "read_file",
        "description": (
            "Read the contents of exactly one existing file from the workspace. "
            "Paths are relative to the workspace root. "
            "You must provide a non-empty file path."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": (
                        "Path relative to the workspace root, "
                        "for example 'src/main.py'."
                    )
                }
            },
            "required": ["path"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "write_file",
        "description": (
            "Write complete content to exactly one file in the workspace. "
            "Paths are relative to the workspace root. "
            "This overwrites the existing file."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": (
                        "Path relative to the workspace root, "
                        "for example 'hello.py'."
                    )
                },
                "content": {
                    "type": "string",
                    "description": "The complete content to write."
                }
            },
            "required": ["path", "content"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "run_command",
        "description": (
            "Run one command in the workspace and return its exit code, "
            "stdout, and stderr. The command runs from the workspace root. "
            "Use this tool when you need to execute a program or verify code."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": (
                        "The command to execute, for example "
                        "'python hello.py'."
                    )
                },
                "timeout": {
                    "type": "integer",
                    "description": (
                        "Maximum execution time in seconds. "
                        "Use a value between 1 and 30."
                    ),
                    "minimum": 1,
                    "maximum": 30
                }
            },
            "required": ["command"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "git_status",
        "description": (
            "Show the current Git working-tree status of the workspace. "
            "Use this when you need to understand which files are modified, "
            "staged, or untracked. This tool takes no arguments."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "list_files",
        "description": (
            "List the immediate files and directories inside a workspace directory. "
            "Use this when you need to discover the workspace contents before "
            "reading or modifying files. Paths are relative to the workspace root. "
            "The default path is the workspace root. This tool does not recursively "
            "list files."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": (
                        "Directory path relative to the workspace root. "
                        "Use '.' or omit the argument to list the workspace root. "
                        "For example, 'src'."
                    ),
                    "default": "."
                }
            },
            "required": [],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "search_files",
        "description": (
            "Search text files recursively inside the workspace for a given "
            "text string. Returns matching file paths, line numbers, and "
            "matching lines. Use this when you need to find where a function, "
            "class, variable, error message, or other text appears in the "
            "codebase."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Text to search for. The search is case-insensitive."
                    )
                },
                "path": {
                    "type": "string",
                    "description": (
                        "Directory relative to the workspace root to search. "
                        "Use '.' to search the entire workspace."
                    ),
                    "default": "."
                }
            },
            "required": ["query"],
            "additionalProperties": False
        }
    },
]

def execute_tool(name, arguments):
    """
    Execute a tool requested by the LLM using the tool registry.
    """

    tool_function = TOOL_FUNCTIONS.get(name)

    if tool_function is None:
        return f"Unknown tool: {name}"

    try:
        return tool_function(**arguments)
    except TypeError as e:
        return f"Error executing tool '{name}': {e}"

def execute_tool_call(name, arguments_json):
    """
    Parse JSON arguments and execute the requested tool.
    """
    try:
        arguments = json.loads(arguments_json)
    except json.JSONDecodeError:
        return "Error: invalid tool arguments."
    if not isinstance(arguments, dict):
        return "Error: tool arguments must be a JSON object."
    return execute_tool(name, arguments)