import json
from unittest.mock import Mock, patch

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

    try:
        agent.update_plan_status(0, "invalid")
        assert False
    except ValueError:
        pass