import json
from pathlib import Path


REQUIRED_FIELDS = {
    "task_id",
    "description",
    "setup",
    "success_condition",
}


def load_tasks(path):
    path = Path(path)

    with open(path, "r", encoding="utf-8") as file:
        tasks = json.load(file)

    if not isinstance(tasks, list):
        raise ValueError("tasks file must contain a list")

    for task in tasks:
        if not isinstance(task, dict):
            raise ValueError("each task must be an object")

        missing = REQUIRED_FIELDS - task.keys()

        if missing:
            raise ValueError(
                f"task is missing required fields: {sorted(missing)}"
            )

        if not isinstance(task["task_id"], str):
            raise ValueError("task_id must be a string")

        if not isinstance(task["description"], str):
            raise ValueError("description must be a string")

        if not isinstance(task["setup"], dict):
            raise ValueError("setup must be an object")

        if not isinstance(task["success_condition"], dict):
            raise ValueError(
                "success_condition must be an object"
            )

    return tasks