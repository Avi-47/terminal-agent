from src.tools import execute_tool_call
from src.tools import run_command

def test_execute_tool_call_rejects_invalid_json():
    result = execute_tool_call(
        "read_file",
        "{invalid json",
    )
    assert result == "Error: invalid tool arguments."

def test_execute_tool_call_rejects_non_object_json():
    result = execute_tool_call(
        "read_file",
        "[]",
    )
    assert result == "Error: tool arguments must be a JSON object."

def test_execute_tool_call_rejects_json_string():
    result = execute_tool_call(
        "read_file",
        '"hello"',
    )
    assert result == "Error: tool arguments must be a JSON object."

def test_execute_tool_call_rejects_non_string_arguments():
    result = execute_tool_call(
        "read_file",
        None,
    )
    assert result == "Error: tool arguments must be a JSON string."

def test_execute_tool_rejects_missing_required_argument():
    result = execute_tool_call(
        "read_file",
        "{}",
    )
    assert result.startswith("Error executing tool 'read_file':")

def test_execute_tool_rejects_unexpected_argument():
    result = execute_tool_call(
        "read_file",
        '{"path": "src/main.py", "unexpected": true}',
    )
    assert result.startswith("Error executing tool 'read_file':")

def test_execute_tool_rejects_unknown_tool():
    result = execute_tool_call(
        "delete_everything",
        "{}",
    )
    assert result == "Unknown tool: delete_everything"

def test_run_command_rejects_python_os_system():
    result = run_command(
        'python -c "import os; os.system(\'del *\')"'
    )
    assert result.startswith("Error:")


def test_run_command_rejects_python_subprocess():
    result = run_command(
        'python -c "import subprocess; subprocess.run(\'cmd /c dir\')"'
    )
    assert result.startswith("Error:")


def test_run_command_allows_safe_python():
    result = run_command(
        'python -c "print(\'hello\')"'
    )
    assert "Exit code: 0" in result
    assert "hello" in result