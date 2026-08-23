from pathlib import Path
import shlex
import subprocess

def _run_command(workspace, command):
    if not isinstance(command, str) or not command.strip():
        return False
    try:
        args = shlex.split(command)
        if not args:
            return False
        if Path(args[0]).name.lower() not in {
            "python",
            "python.exe",
        }:
            return False
        result = subprocess.run(
            args,
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=10,
            shell=False,
        )
        return result.returncode == 0
    except (
        OSError,
        subprocess.TimeoutExpired,
        ValueError,
    ):
        return False
    
def _safe_path(workspace, relative_path):
    if not isinstance(relative_path, str) or not relative_path.strip():
        return None
    workspace = Path(workspace).resolve()
    candidate = (workspace / relative_path).resolve()
    try:
        candidate.relative_to(workspace)
    except ValueError:
        return None
    return candidate

def _tool_result_contains(tool_results, text):
    if not isinstance(tool_results, list):
        return False
    if not isinstance(text, str):
        return False
    needle = text.lower()
    for result in tool_results:
        if not isinstance(result, str):
            continue
        if needle in result.lower():
            return True
    return False

def _response_contains(response, text):
    if not isinstance(response, str):
        return False
    if not isinstance(text, str):
        return False
    return text.lower() in response.lower()

def evaluate_condition(workspace, condition, response=None,):
    if not isinstance(condition, dict):
        return False
    condition_type = condition.get("type")
    if condition_type == "command_succeeds":
        return _run_command(
            workspace,
            condition.get("command"),
        )
    if condition_type == "file_exists":
        path = _safe_path(
            workspace,
            condition.get("path"),
        )
        if path is None:
            return False
        return path.is_file()
    if condition_type == "tool_result_contains":
        return _tool_result_contains(
            condition.get("tool_results"),
            condition.get("text"),
        )
    if condition_type == "file_contains":
        path = _safe_path(
            workspace,
            condition.get("path"),
        )
        if path is None or not path.is_file():
            return False
        text = condition.get("text")
        if not isinstance(text, str):
            return False
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return False
        return text in content
    if condition_type == "response_contains":
        if not isinstance(response, str):
            return False
        text = condition.get("text")
        if not isinstance(text, str):
            return False
        return text.lower() in response.lower()
    return False