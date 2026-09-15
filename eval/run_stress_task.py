import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from src.agent import Agent
from .run_task import run_task


def load_stress_tasks(path):
    path = Path(path)

    with open(path, "r", encoding="utf-8") as file:
        tasks = json.load(file)

    if not isinstance(tasks, list):
        raise ValueError(
            "Stress task file must contain a list"
        )

    return tasks


def create_client():
    load_dotenv()

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. "
            "Add it to your .env file."
        )

    return OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
    )


def main():
    tasks_path = (
        Path(__file__).resolve().parent
        / "stress_tasks.json"
    )

    tasks = load_stress_tasks(tasks_path)

    client = create_client()

    for task in tasks:
        print()
        print("=" * 70)
        print(
            f"Running stress task: "
            f"{task['task_id']}"
        )
        print("=" * 70)

        result = run_task(
            task,
            client=client,
            agent_factory=Agent,
            use_repo_context=True,
            enable_validation=True,
            enable_reviewer=False,
        )

        print()
        print("RESULT")
        print("-" * 70)
        print(json.dumps(result, indent=2))

        if result["passed"]:
            print()
            print("STRESS TASK PASSED")
        else:
            print()
            print("STRESS TASK FAILED")


if __name__ == "__main__":
    main()