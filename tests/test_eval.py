import json
from pathlib import Path
from eval.evaluator import evaluate_condition
from eval.tasks import load_tasks
from eval.workspace import (
    create_workspace,
    cleanup_workspace,
)
from eval.run_task import run_task
from eval.results import (
    write_result,
    calculate_summary,
)

created_workspace = None

class FakeAgent:
    def __init__(self, client, workspace=None, use_repo_context=True,):
        global created_workspace
        created_workspace = workspace
        self.workspace = workspace
        self.use_repo_context = use_repo_context

    def run(self, prompt):
        file_path = self.workspace / "hello.py"

        file_path.write_text(
            "print('Hello')",
            encoding="utf-8",
        )
        return "Created hello.py"
    
class FakeTelemetry:
    def __init__(self):
        self.data = {
            "turns": 3,
            "tool_calls": 2,
            "duration_seconds": 1.5,
            "model": "fake-model",
        }

class FakeAgentWithTelemetry(FakeAgent):
    def __init__(self, client, workspace=None, use_repo_context=True,):
        super().__init__(
            client,
            workspace,
            use_repo_context,
        )
        self.telemetry = FakeTelemetry()

def test_write_result(tmp_path):
    results_path = tmp_path / "results.jsonl"
    result = {
        "task_id": "test_task",
        "passed": True,
        "turns": 3,
        "tool_calls": 2,
        "duration_seconds": 1.5,
        "model": "fake-model",
    }
    write_result(
        results_path,
        result,
    )
    lines = results_path.read_text(
        encoding="utf-8"
    ).splitlines()
    assert len(lines) == 1
    loaded = json.loads(lines[0])
    assert loaded == result

def test_calculate_summary():
    results = [
        {
            "task_id": "task_1",
            "passed": True,
            "turns": 4,
            "tool_calls": 2,
            "duration_seconds": 10.0,
        },
        {
            "task_id": "task_2",
            "passed": True,
            "turns": 6,
            "tool_calls": 4,
            "duration_seconds": 20.0,
        },
        {
            "task_id": "task_3",
            "passed": False,
            "turns": 5,
            "tool_calls": 3,
            "duration_seconds": 15.0,
        },
    ]
    summary = calculate_summary(results)
    assert summary["total_tasks"] == 3
    assert summary["passed_tasks"] == 2
    assert summary["pass_rate"] == 2 / 3 * 100
    assert summary["average_turns"] == 5.0
    assert summary["average_tool_calls"] == 3.0
    assert summary["average_duration"] == 15.0

def test_calculate_summary_empty():
    summary = calculate_summary([])
    assert summary == {
        "total_tasks": 0,
        "passed_tasks": 0,
        "pass_rate": 0.0,
        "average_turns": 0.0,
        "average_tool_calls": 0.0,
        "average_duration": 0.0,
    }

def test_response_contains_fails_when_text_missing():
    workspace = create_workspace({})
    try:
        condition = {
            "type": "response_contains",
            "text": "not present",
        }
        assert evaluate_condition(
            workspace,
            condition,
            response="The evaluation system is working.",
        ) is False
    finally:
        cleanup_workspace(workspace)

def test_response_contains():
    workspace = create_workspace({})
    try:
        condition = {
            "type": "response_contains",
            "text": "evaluation system",
        }
        assert evaluate_condition(
            workspace,
            condition,
            response="The Evaluation System is working.",
        ) is True
    finally:
        cleanup_workspace(workspace)

def test_calculate_summary_without_metrics():
    results = [
        {
            "task_id": "task_1",
            "passed": True,
        },
        {
            "task_id": "task_2",
            "passed": False,
        },
    ]
    summary = calculate_summary(results)
    assert summary["total_tasks"] == 2
    assert summary["passed_tasks"] == 1
    assert summary["pass_rate"] == 50.0
    assert summary["average_turns"] == 0.0
    assert summary["average_tool_calls"] == 0.0
    assert summary["average_duration"] == 0.0

def test_write_result_appends(tmp_path):
    results_path = tmp_path / "results.jsonl"
    first = {
        "task_id": "task_1",
        "passed": True,
    }
    second = {
        "task_id": "task_2",
        "passed": False,
    }
    write_result(results_path, first)
    write_result(results_path, second)
    lines = results_path.read_text(
        encoding="utf-8"
    ).splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0]) == first
    assert json.loads(lines[1]) == second

def test_run_task_includes_telemetry():
    task = {
        "task_id": "telemetry_test",
        "description": "Create hello.py",
        "setup": {},
        "success_condition": {
            "type": "file_exists",
            "path": "hello.py",
        },
    }
    result = run_task(
        task,
        client=None,
        agent_factory=FakeAgentWithTelemetry,
    )
    assert result["task_id"] == "telemetry_test"
    assert result["passed"] is True
    assert result["turns"] == 3
    assert result["tool_calls"] == 2
    assert result["duration_seconds"] == 1.5
    assert result["model"] == "fake-model"

def test_run_task_cleans_up_workspace():
    global created_workspace
    created_workspace = None
    task = {
        "task_id": "cleanup_test",
        "description": "Create a file",
        "setup": {},
        "success_condition": {
            "type": "file_exists",
            "path": "hello.py",
        },
    }
    run_task(
        task,
        client=None,
        agent_factory=FakeAgent,
    )
    assert created_workspace is not None
    assert not created_workspace.exists()

def test_run_task_success():
    task = {
        "task_id": "create_python_file",
        "description": "Create hello.py",
        "setup": {},
        "success_condition": {
            "type": "file_contains",
            "path": "hello.py",
            "text": "print",
        },
    }
    result = run_task(
        task,
        client=None,
        agent_factory=FakeAgent,
    )
    assert result["task_id"] == "create_python_file"
    assert result["passed"] is True
    assert result["response"] == "Created hello.py"
    
def test_command_succeeds(tmp_path):
    file_path = tmp_path / "hello.py"
    file_path.write_text(
        "print('Hello')",
        encoding="utf-8",
    )
    condition = {
        "type": "command_succeeds",
        "command": "python hello.py",
    }
    assert evaluate_condition(tmp_path, condition) is True

def test_command_fails(tmp_path):
    file_path = tmp_path / "broken.py"
    file_path.write_text(
        "raise RuntimeError('broken')",
        encoding="utf-8",
    )
    condition = {
        "type": "command_succeeds",
        "command": "python broken.py",
    }
    assert evaluate_condition(tmp_path, condition) is False

def test_create_workspace(tmp_path):
    setup = {
        "files": {
            "info.txt": "Evaluation works.",
            "src/example.py": "print('Hello')",
        }
    }
    workspace = create_workspace(setup)
    try:
        assert workspace.exists()
        assert workspace.is_dir()
        assert (
            workspace / "info.txt"
        ).read_text(encoding="utf-8") == "Evaluation works."
        assert (
            workspace / "src" / "example.py"
        ).read_text(encoding="utf-8") == "print('Hello')"
    finally:
        cleanup_workspace(workspace)

def test_create_empty_workspace():
    workspace = create_workspace({})
    try:
        assert workspace.exists()
        assert workspace.is_dir()
    finally:
        cleanup_workspace(workspace)

def test_cleanup_workspace():
    workspace = create_workspace(
        {
            "files": {
                "test.txt": "hello",
            }
        }
    )
    assert workspace.exists()
    cleanup_workspace(workspace)
    assert not workspace.exists()

import pytest


def test_create_workspace_rejects_path_traversal():
    with pytest.raises(ValueError):
        create_workspace(
            {
                "files": {
                    "../outside.txt": "should not be created",
                }
            }
        )

def test_command_condition_rejects_unsupported_program(tmp_path):
    condition = {
        "type": "command_succeeds",
        "command": "git status",
    }
    assert evaluate_condition(tmp_path, condition) is False

def test_load_tasks():
    tasks_path = (
        Path(__file__).resolve().parent.parent
        / "eval"
        / "tasks.json"
    )
    tasks = load_tasks(tasks_path)
    assert len(tasks) == 13

def test_load_tasks_rejects_missing_field(tmp_path):
    tasks_path = tmp_path / "tasks.json"
    tasks_path.write_text(
        """
        [
            {
                "task_id": "broken",
                "description": "Broken task"
            }
        ]
        """,
        encoding="utf-8",
    )
    try:
        load_tasks(tasks_path)
        assert False, "Expected ValueError"
    except ValueError as error:
        assert "missing required fields" in str(error)

def test_load_tasks_rejects_non_list(tmp_path):
    tasks_path = tmp_path / "tasks.json"
    tasks_path.write_text(
        '{"task_id": "wrong"}',
        encoding="utf-8",
    )
    try:
        load_tasks(tasks_path)
        assert False, "Expected ValueError"
    except ValueError as error:
        assert "must contain a list" in str(error)

def test_file_exists_condition(tmp_path):
    file_path = tmp_path / "hello.py"
    file_path.write_text(
        "print('Hello')",
        encoding="utf-8",
    )
    condition = {
        "type": "file_exists",
        "path": "hello.py",
    }
    assert evaluate_condition(tmp_path, condition) is True

def test_file_exists_missing_file(tmp_path):
    condition = {
        "type": "file_exists",
        "path": "missing.py",
    }
    assert evaluate_condition(tmp_path, condition) is False

def test_file_contains_condition(tmp_path):
    file_path = tmp_path / "hello.py"
    file_path.write_text(
        "print('Hello')",
        encoding="utf-8",
    )
    condition = {
        "type": "file_contains",
        "path": "hello.py",
        "text": "print",
    }
    assert evaluate_condition(tmp_path, condition) is True

def test_file_contains_missing_text(tmp_path):
    file_path = tmp_path / "hello.py"
    file_path.write_text(
        "print('Hello')",
        encoding="utf-8",
    )
    condition = {
        "type": "file_contains",
        "path": "hello.py",
        "text": "Goodbye",
    }
    assert evaluate_condition(tmp_path, condition) is False

def test_condition_cannot_escape_workspace(tmp_path):
    outside_file = tmp_path.parent / "outside.txt"
    outside_file.write_text(
        "secret",
        encoding="utf-8",
    )
    condition = {
        "type": "file_exists",
        "path": "../outside.txt",
    }
    assert evaluate_condition(tmp_path, condition) is False

def test_unknown_condition_returns_false(tmp_path):
    condition = {
        "type": "something_we_do_not_support",
    }
    assert evaluate_condition(tmp_path, condition) is False

def test_evaluation_tasks_have_required_fields():
    tasks_path = (
        Path(__file__).resolve().parent.parent
        / "eval"
        / "tasks.json"
    )
    with open(tasks_path, "r", encoding="utf-8") as file:
        tasks = json.load(file)

    assert isinstance(tasks, list)
    assert len(tasks) == 13

    for task in tasks:
        assert "task_id" in task
        assert "description" in task
        assert "setup" in task
        assert "success_condition" in task