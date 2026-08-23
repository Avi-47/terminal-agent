from unittest.mock import Mock
import pytest
from src.agent import Agent
import src.tools as tools

def test_agent_can_configure_workspace(tmp_path):
    original_workspace = tools.WORKSPACE_ROOT
    try:
        Agent(
            client=None,
            workspace=tmp_path,
        )
        assert tools.WORKSPACE_ROOT == tmp_path.resolve()
    finally:
        tools.set_workspace_root(original_workspace)

def test_agent_workspace_is_used_by_file_tools(tmp_path):
    import src.tools as tools
    original_workspace = tools.WORKSPACE_ROOT
    try:
        Agent(
            client=None,
            workspace=tmp_path,
        )
        result = tools.write_file(
            "hello.py",
            "print('Hello')",
        )
        assert "Successfully wrote file" in result
        hello_file = tmp_path / "hello.py"
        assert hello_file.exists()
        assert hello_file.read_text(encoding="utf-8") == "print('Hello')"
    finally:
        tools.set_workspace_root(original_workspace)

def make_agent():
    return Agent(Mock())

def test_update_plan_status():
    agent = make_agent()
    agent.plan = [
        {"task": "Inspect code", "status": "pending"},
        {"task": "Fix bug", "status": "pending"},
    ]
    agent.update_plan_status(0, "in_progress")
    assert agent.plan[0]["status"] == "in_progress"

def test_update_plan_status_rejects_invalid_status():
    agent = make_agent()
    agent.plan = [
        {"task": "Inspect code", "status": "pending"},
    ]
    with pytest.raises(ValueError):
        agent.update_plan_status(0, "invalid")

def test_update_plan_status_rejects_invalid_index():
    agent = make_agent()
    agent.plan = [
        {"task": "Inspect code", "status": "pending"},
    ]
    with pytest.raises(IndexError):
        agent.update_plan_status(5, "done")

def test_start_plan_task():
    agent = make_agent()
    agent.plan = [
        {"task": "Inspect code", "status": "pending"},
    ]
    agent.start_plan_task(0)
    assert agent.plan[0]["status"] == "in_progress"

def test_finish_plan_task():
    agent = make_agent()
    agent.plan = [
        {"task": "Inspect code", "status": "in_progress"},
    ]
    agent.finish_plan_task(0)
    assert agent.plan[0]["status"] == "done"

def test_create_plan_adds_pending_status():
    agent = make_agent()
    class FakeResponse:
        output_text = (
            '{"needs_plan": true, '
            '"tasks": ['
            '{"task": "Inspect code"}, '
            '{"task": "Fix bug"}'
            ']}'
        )
    # We don't want to call the real API.
    import src.agent as agent_module
    original = agent_module.create_response
    agent_module.create_response = lambda *args, **kwargs: FakeResponse()
    try:
        plan = agent.create_plan("Inspect and fix a bug")
    finally:
        agent_module.create_response = original
    assert plan == [
        {"task": "Inspect code", "status": "pending"},
        {"task": "Fix bug", "status": "pending"},
    ]

def test_create_plan_returns_empty_for_simple_request():
    agent = make_agent()
    class FakeResponse:
        output_text = '{"needs_plan": false, "tasks": []}'
    import src.agent as agent_module
    original = agent_module.create_response
    agent_module.create_response = lambda *args, **kwargs: FakeResponse()
    try:
        plan = agent.create_plan("Read src/main.py")
    finally:
        agent_module.create_response = original
    assert plan == []

def test_display_plan_does_nothing_when_empty(capsys):
    agent = make_agent()
    agent.plan = []
    agent.display_plan()
    captured = capsys.readouterr()
    assert captured.out == ""

def test_display_plan_shows_statuses(capsys):
    agent = make_agent()
    agent.plan = [
        {"task": "Inspect code", "status": "pending"},
        {"task": "Fix bug", "status": "in_progress"},
        {"task": "Run tests", "status": "done"},
    ]
    agent.display_plan()
    captured = capsys.readouterr()
    assert "[ ] Inspect code" in captured.out
    assert "[>] Fix bug" in captured.out
    assert "[x] Run tests" in captured.out

def test_agent_routes_tool_calls_through_execute_tool_call():
    from unittest.mock import patch
    class FakeItem:
        type = "function_call"
        name = "read_file"
        arguments = '{"path": "src/agent.py"}'
        call_id = "call_123"
    class PlanResponse:
        output = []
        output_text = '{"needs_plan": false, "tasks": []}'
    class ToolResponse:
        output = [FakeItem()]
        output_text = ""
    class FinalResponse:
        output = []
        output_text = "Done."
    class FakeClient:
        pass
    agent = Agent(FakeClient())
    with patch(
        "src.agent.create_response",
        side_effect=[
            PlanResponse(),
            ToolResponse(),
            FinalResponse(),
        ],
    ), patch(
        "src.agent.execute_tool_call",
        return_value="safe tool result",
    ) as mock_execute:
        result = agent.run("Read src/agent.py")
    mock_execute.assert_called_once_with(
        "read_file",
        '{"path": "src/agent.py"}',
    )
    assert result == "Done."

def test_agent_uses_tool_layer_for_rejected_command():
    from unittest.mock import patch
    class FakeItem:
        type = "function_call"
        name = "run_command"
        arguments = '{"command": "powershell Get-ChildItem"}'
        call_id = "call_456"
    class PlanResponse:
        output = []
        output_text = '{"needs_plan": false, "tasks": []}'
    class ToolResponse:
        output = [FakeItem()]
        output_text = ""
    class FinalResponse:
        output = []
        output_text = "I cannot run that command."
    class FakeClient:
        pass
    agent = Agent(FakeClient())
    with patch(
        "src.agent.create_response",
        side_effect=[
            PlanResponse(),
            ToolResponse(),
            FinalResponse(),
        ],
    ), patch(
        "src.agent.execute_tool_call",
        return_value="Error: command is not allowed: powershell",
    ) as mock_execute:
        result = agent.run(
            "Run powershell Get-ChildItem"
        )
    mock_execute.assert_called_once_with(
        "run_command",
        '{"command": "powershell Get-ChildItem"}',
    )
    assert result == "I cannot run that command."

def test_create_plan_returns_empty_for_invalid_json():
    agent = make_agent()

    class FakeResponse:
        output_text = "not valid json"

    import src.agent as agent_module
    original = agent_module.create_response
    agent_module.create_response = lambda *args, **kwargs: FakeResponse()

    try:
        plan = agent.create_plan("Do something")
    finally:
        agent_module.create_response = original

    assert plan == []


def test_create_plan_returns_empty_for_json_list():
    agent = make_agent()

    class FakeResponse:
        output_text = '["not", "an", "object"]'

    import src.agent as agent_module
    original = agent_module.create_response
    agent_module.create_response = lambda *args, **kwargs: FakeResponse()

    try:
        plan = agent.create_plan("Do something")
    finally:
        agent_module.create_response = original

    assert plan == []


def test_create_plan_returns_empty_for_invalid_tasks():
    agent = make_agent()

    class FakeResponse:
        output_text = (
            '{"needs_plan": true, '
            '"tasks": "not a list"}'
        )

    import src.agent as agent_module
    original = agent_module.create_response
    agent_module.create_response = lambda *args, **kwargs: FakeResponse()

    try:
        plan = agent.create_plan("Do something")
    finally:
        agent_module.create_response = original

    assert plan == []


def test_create_plan_ignores_invalid_task_items():
    agent = make_agent()

    class FakeResponse:
        output_text = (
            '{"needs_plan": true, '
            '"tasks": ['
            '{"task": "Inspect code"}, '
            '{"bad": "item"}, '
            '"invalid", '
            '{"task": 123}'
            ']}'
        )

    import src.agent as agent_module
    original = agent_module.create_response
    agent_module.create_response = lambda *args, **kwargs: FakeResponse()

    try:
        plan = agent.create_plan("Inspect code")
    finally:
        agent_module.create_response = original

    assert plan == [
        {"task": "Inspect code", "status": "pending"},
    ]

def test_agent_blocks_git_commit_without_confirmation():
    from unittest.mock import patch

    class FakeItem:
        type = "function_call"
        name = "git_commit"
        arguments = '{"message": "automatic commit"}'
        call_id = "call_commit"

    class PlanResponse:
        output = []
        output_text = '{"needs_plan": false, "tasks": []}'

    class ToolResponse:
        output = [FakeItem()]
        output_text = ""

    class FinalResponse:
        output = []
        output_text = "I need confirmation before committing."

    class FakeClient:
        pass

    agent = Agent(FakeClient())

    with patch(
        "src.agent.create_response",
        side_effect=[
            PlanResponse(),
            ToolResponse(),
            FinalResponse(),
        ],
    ), patch(
        "src.agent.execute_tool_call",
    ) as mock_execute:
        result = agent.run(
            "Commit all my changes without asking me."
        )

    mock_execute.assert_not_called()
    assert result == "I need confirmation before committing."

def test_agent_allows_git_commit_after_confirmation():
    from unittest.mock import patch

    class FakeItem:
        type = "function_call"
        name = "git_commit"
        arguments = '{"message": "test commit"}'
        call_id = "call_commit"

    class PlanResponse:
        output = []
        output_text = '{"needs_plan": false, "tasks": []}'

    class ToolResponse:
        output = [FakeItem()]
        output_text = ""

    class FinalResponse:
        output = []
        output_text = "Commit created."

    class FakeClient:
        pass

    confirm_callback = Mock(return_value=True)
    agent = Agent(
        FakeClient(),
        confirm_callback=confirm_callback,
    )

    with patch(
        "src.agent.create_response",
        side_effect=[
            PlanResponse(),
            ToolResponse(),
            FinalResponse(),
        ],
    ), patch(
        "src.agent.execute_tool_call",
        return_value="Commit created successfully.",
    ) as mock_execute:
        result = agent.run(
            'Commit my changes with message "test commit".'
        )

    confirm_callback.assert_called_once_with()
    mock_execute.assert_called_once_with(
        "git_commit",
        '{"message": "test commit"}',
    )
    assert result == "Commit created."