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
    workspace = create_workspace(task["setup"])
    agent = None

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

        telemetry = getattr(agent, "telemetry", None)

        if telemetry is not None:
            data = telemetry.data

            result = {
                "task_id": task["task_id"],
                "passed": passed,
                "turns": data.get("turns", 0),
                "tool_calls": data.get("tool_calls", 0),
                "duration_seconds": data.get(
                    "duration_seconds",
                    0,
                ),
                "model": data.get("model"),
                "tools": data.get("tools", []),
                "status": data.get(
                    "status",
                    "success",
                ),
            }
        else:
            result = {
                "task_id": task["task_id"],
                "passed": passed,
            }

        result["response"] = response

        return result

    except Exception as error:
        telemetry = getattr(agent, "telemetry", None)

        if telemetry is not None:
            data = telemetry.data

            return {
                "task_id": task["task_id"],
                "passed": False,
                "turns": data.get("turns", 0),
                "tool_calls": data.get("tool_calls", 0),
                "duration_seconds": data.get(
                    "duration_seconds",
                    0,
                ),
                "model": data.get("model"),
                "tools": data.get("tools", []),
                "response": None,
                "status": data.get(
                    "status",
                    "error",
                ),
                "error": str(error),
            }

        return {
            "task_id": task["task_id"],
            "passed": False,
            "turns": 0,
            "tool_calls": 0,
            "duration_seconds": 0,
            "model": None,
            "tools": [],
            "response": None,
            "status": "error",
            "error": str(error),
        }

    finally:
        if agent is not None:
            try:
                agent.stop_mcp()
            except Exception:
                pass

        cleanup_workspace(workspace)