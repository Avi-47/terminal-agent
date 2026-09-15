from .evaluator import evaluate_condition
from .workspace import (
    create_workspace,
    cleanup_workspace,
)
from src.agent import Agent


def run_task(
    task,
    client,
    agent_factory=Agent,
    use_repo_context=True,
    enable_validation=True,
    enable_reviewer=True,
    enable_mcp=False,
):
    workspace = create_workspace(
        task["setup"]
    )

    try:
        agent_kwargs = {
            "workspace": workspace,
            "use_repo_context": use_repo_context,
            "enable_validation": enable_validation,
            "enable_reviewer": enable_reviewer,
        }

        if enable_mcp:
            agent_kwargs["enable_mcp"] = True

        agent = agent_factory(
            client,
            **agent_kwargs,
        )

        stress_config = task.get("stress_test")

        if stress_config is not None:
            response = agent.run(
                task["description"],
                stress_config=stress_config,
            )
        else:
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
                "tools": data.get("tools", []),
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