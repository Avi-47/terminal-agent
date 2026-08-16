import subprocess
from unittest.mock import patch

from src.tools import (
    git_add,
    git_commit,
    git_diff,
    TOOL_FUNCTIONS,
    TOOLS,
)


def make_git_result(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(
        args=["git"],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def test_git_diff_returns_diff():
    diff = (
        "diff --git a/src/agent.py b/src/agent.py\n"
        "--- a/src/agent.py\n"
        "+++ b/src/agent.py\n"
        "@@ -1 +1 @@\n"
        "-old\n"
        "+new"
    )

    with patch("src.tools.subprocess.run") as mock_run:
        mock_run.return_value = make_git_result(
            stdout=diff
        )

        result = git_diff()

    assert result == diff
    mock_run.assert_called_once_with(
        ["git", "diff"],
        cwd=mock_run.call_args.kwargs["cwd"],
        capture_output=True,
        text=True,
        shell=False,
        timeout=10,
    )


def test_git_diff_no_changes():
    with patch("src.tools.subprocess.run") as mock_run:
        mock_run.return_value = make_git_result()

        result = git_diff()

    assert result == "Git working tree has no unstaged changes."


def test_git_diff_handles_git_failure():
    with patch("src.tools.subprocess.run") as mock_run:
        mock_run.return_value = make_git_result(
            returncode=128,
            stderr="fatal: not a git repository"
        )

        result = git_diff()

    assert result == (
        "Error: git diff failed:\n"
        "fatal: not a git repository"
    )


def test_git_diff_handles_timeout():
    with patch("src.tools.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd=["git", "diff"],
            timeout=10,
        )

        result = git_diff()

    assert result == "Error: git diff timed out."


def test_git_diff_handles_git_unavailable():
    with patch("src.tools.subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError()

        result = git_diff()

    assert result == (
        "Error: git is not installed or not available on PATH."
    )


def test_git_add_rejects_empty_paths():
    assert git_add([]) == "Error: paths must not be empty."


def test_git_add_rejects_non_list():
    assert git_add("src/agent.py") == "Error: paths must be a list."


def test_git_add_rejects_empty_path():
    assert (
        git_add([""])
        == "Error: each path must be a non-empty string."
    )


def test_git_add_rejects_path_outside_workspace():
    result = git_add(["../outside.txt"])

    assert result.startswith(
        "Error: path is outside the workspace:"
    )


def test_git_add_stages_specific_path():
    with patch("src.tools.subprocess.run") as mock_run:
        mock_run.return_value = make_git_result()

        result = git_add(["src/agent.py"])

    assert result == "Successfully staged 1 path(s)."

    args, kwargs = mock_run.call_args

    assert args[0] == [
        "git",
        "add",
        "--",
        "src/agent.py",
    ]
    assert kwargs["shell"] is False
    assert kwargs["timeout"] == 10


def test_git_add_handles_git_failure():
    with patch("src.tools.subprocess.run") as mock_run:
        mock_run.return_value = make_git_result(
            returncode=128,
            stderr="fatal: not a git repository"
        )

        result = git_add(["src/agent.py"])

    assert result == (
        "Error: git add failed:\n"
        "fatal: not a git repository"
    )


def test_git_commit_rejects_empty_message():
    assert (
        git_commit("")
        == "Error: commit message must not be empty."
    )


def test_git_commit_rejects_multiline_message():
    assert (
        git_commit("first line\nsecond line")
        == "Error: commit message must be a single line."
    )


def test_git_commit_success():
    with patch("src.tools.subprocess.run") as mock_run:
        mock_run.return_value = make_git_result(
            stdout="[main abc1234] test commit"
        )

        result = git_commit("test commit")

    assert result == "[main abc1234] test commit"

    args, kwargs = mock_run.call_args

    assert args[0] == [
        "git",
        "commit",
        "-m",
        "test commit",
    ]
    assert kwargs["shell"] is False
    assert kwargs["timeout"] == 10


def test_git_commit_handles_git_failure():
    with patch("src.tools.subprocess.run") as mock_run:
        mock_run.return_value = make_git_result(
            returncode=1,
            stderr="nothing to commit"
        )

        result = git_commit("test commit")

    assert result == (
        "Error: git commit failed:\n"
        "nothing to commit"
    )


def test_git_commit_handles_timeout():
    with patch("src.tools.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd=["git", "commit"],
            timeout=10,
        )

        result = git_commit("test commit")

    assert result == "Error: git commit timed out."


def test_git_tools_are_registered():
    assert "git_status" in TOOL_FUNCTIONS
    assert "git_diff" in TOOL_FUNCTIONS
    assert "git_add" in TOOL_FUNCTIONS
    assert "git_commit" in TOOL_FUNCTIONS


def test_git_tools_are_exposed_to_model():
    tool_names = {
        tool["name"]
        for tool in TOOLS
    }

    assert "git_status" in tool_names
    assert "git_diff" in tool_names
    assert "git_add" in tool_names
    assert "git_commit" in tool_names


def test_git_commit_is_not_automatically_triggered_by_registration():
    commit_tool = next(
        tool
        for tool in TOOLS
        if tool["name"] == "git_commit"
    )

    description = commit_tool["description"].lower()

    assert "explicitly asks" in description
    assert "automatically" in description