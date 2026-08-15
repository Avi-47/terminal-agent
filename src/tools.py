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
    }
]


def execute_tool(name, arguments):
    """
    Execute a tool requested by the LLM.
    """

    if name == "read_file":
        path = arguments.get("path")

        if not path:
            return "Error: path is required."

        return read_file(path)

    if name == "write_file":
        path = arguments.get("path")
        content = arguments.get("content")

        if not path:
            return "Error: path is required."

        if content is None:
            return "Error: content is required."

        return write_file(path, content)

    if name == "run_command":
        command = arguments.get("command")
        timeout = arguments.get("timeout", 10)

        if not command:
            return "Error: command is required."

        return run_command(command, timeout)

    return f"Unknown tool: {name}"


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