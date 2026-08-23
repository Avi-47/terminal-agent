from .evaluator import evaluate_condition
from .workspace import (
    create_workspace,
    cleanup_workspace,
)
from src.agent import Agent

def run_task(task, client, agent_factory=Agent):
    workspace = create_workspace(
        task["setup"]
    )
    try:
        agent = agent_factory(
            client,
            workspace=workspace,
        )
        response = agent.run(
            task["description"]
        )
        passed = evaluate_condition(
            workspace,
            task["success_condition"],
            response=response,
        )
        telemetry = getattr(
            agent,
            "telemetry",
            None,
        )
        if telemetry is not None:
            data = telemetry.data
            result = {
                "task_id": task["task_id"],
                "passed": passed,
                "turns": data["turns"],
                "tool_calls": data["tool_calls"],
                "duration_seconds": data["duration_seconds"],
                "model": data["model"],
            }
        else:
            result = {
                "task_id": task["task_id"],
                "passed": passed,
            }
        result["response"] = response
        return result
    finally:
        cleanup_workspace(workspace)