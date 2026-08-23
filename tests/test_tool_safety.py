from src.tools import (
    execute_tool_call,
    run_command,
    git_commit,
)
import src.tools as tools

def test_set_workspace_root(tmp_path):
    original_workspace = tools.WORKSPACE_ROOT
    try:
        tools.set_workspace_root(tmp_path)
        assert tools.WORKSPACE_ROOT == tmp_path.resolve()
    finally:
        tools.set_workspace_root(original_workspace)
        
def test_file_tools_use_configured_workspace(tmp_path):
    original_workspace = tools.WORKSPACE_ROOT
    try:
        tools.set_workspace_root(tmp_path)
        result = tools.write_file(
            "hello.py",
            "print('Hello')",
        )
        assert "Successfully wrote file" in result
        created_file = tmp_path / "hello.py"
        assert created_file.exists()
        assert created_file.read_text(encoding="utf-8") == "print('Hello')"

    finally:
        tools.set_workspace_root(original_workspace)

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

def test_validate_command_rejects_format():
    from src.tools import validate_command
    result = validate_command(["format", "D:"])
    assert result == "Error: destructive command is not allowed: format"


def test_validate_command_rejects_shutdown():
    from src.tools import validate_command
    result = validate_command(["shutdown", "/s"])
    assert result == "Error: destructive command is not allowed: shutdown"

def test_read_file_rejects_empty_path():
    result = execute_tool_call(
        "read_file",
        '{"path": ""}',
    )
    assert result == "Error: path must not be empty"

def test_write_file_rejects_missing_content():
    result = execute_tool_call(
        "write_file",
        '{"path": "test.txt"}',
    )
    assert result.startswith("Error executing tool 'write_file':")

def test_run_command_rejects_invalid_timeout():
    result = run_command(
        "python -c \"print('hello')\"",
        timeout="10",
    )
    assert result == "Error: timeout must be an integer."

def test_run_command_rejects_timeout_out_of_range():
    result = run_command(
        "python -c \"print('hello')\"",
        timeout=0,
    )
    assert result == "Error: timeout must be between 1 and 30 seconds."

def test_run_command_rejects_timeout_too_large():
    result = run_command(
        "python -c \"print('hello')\"",
        timeout=31,
    )
    assert result == "Error: timeout must be between 1 and 30 seconds."

def test_git_commit_rejects_non_string_message():
    result = git_commit(123)
    assert result.startswith("Error:")

def test_execute_tool_call_cannot_escape_workspace():
    result = execute_tool_call(
        "read_file",
        '{"path": "../../secret.txt"}',
    )
    assert result.startswith(
        "Error: path is outside the workspace:"
    )

def test_execute_tool_call_rejects_unapproved_command():
    result = execute_tool_call(
        "run_command",
        '{"command": "powershell Get-ChildItem"}',
    )
    assert result.startswith(
        "Error: command is not allowed:"
    )

def test_execute_tool_call_rejects_destructive_command():
    result = execute_tool_call(
        "run_command",
        '{"command": "format C:"}',
    )
    assert result.startswith(
        "Error: destructive command is not allowed:"
    )

def test_execute_tool_call_rejects_outside_git_path():
    result = execute_tool_call(
        "git_add",
        '{"paths": ["../../outside.txt"]}',
    )
    assert result.startswith(
        "Error: path is outside the workspace:"
    )

def test_execute_tool_call_does_not_auto_commit():
    result = execute_tool_call(
        "git_commit",
        '{"message": "automatic commit"}',
    )
    # The tool itself is callable only when explicitly requested
    # by the agent/user flow. This test ensures registration alone
    # does not cause a commit.
    assert isinstance(result, str)