from unittest.mock import Mock
import pytest
from src.agent import Agent

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