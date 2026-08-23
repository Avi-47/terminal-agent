import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from eval.results import (
    calculate_summary,
    write_result,
)
from eval.run_task import run_task
from eval.tasks import load_tasks

BASE_DIR = Path(__file__).resolve().parent.parent
TASKS_PATH = BASE_DIR / "eval" / "tasks.json"
RESULTS_PATH = BASE_DIR / "eval" / "results.jsonl"

def create_client():
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set."
        )
    return OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
    )

def run_evaluation():
    tasks = load_tasks(TASKS_PATH)
    client = create_client()
    results = []
    print("Running evaluation...\n")
    for index, task in enumerate(tasks, start=1):
        print(
            f"[{index}/{len(tasks)}] "
            f"{task['task_id']}",
            end=" ",
            flush=True,
        )
        result = run_task(
            task,
            client,
        )
        results.append(result)
        write_result(
            RESULTS_PATH,
            result,
        )
        if result["passed"]:
            print("PASS")
        else:
            print("FAIL")
    summary = calculate_summary(results)
    print()
    print("Evaluation Summary")
    print("------------------")
    print(
        f"Tasks:             "
        f"{summary['total_tasks']}"
    )
    print(
        f"Passed:            "
        f"{summary['passed_tasks']}"
    )
    print(
        f"Pass rate:         "
        f"{summary['pass_rate']:.1f}%"
    )
    print(
        f"Avg turns:         "
        f"{summary['average_turns']:.1f}"
    )
    print(
        f"Avg tool calls:    "
        f"{summary['average_tool_calls']:.1f}"
    )
    print(
        f"Avg duration:      "
        f"{summary['average_duration']:.1f}s"
    )
    return summary

if __name__ == "__main__":
    run_evaluation()