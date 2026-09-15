import time
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from .run_task import run_task
from .tasks import load_tasks

TASKS_PATH = Path(__file__).parent / "tasks.json"

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

def summarize(results):
    total = len(results)
    passed = sum(
        result["passed"]
        for result in results
    )
    total_turns = sum(
        result.get("turns", 0)
        for result in results
    )
    total_tool_calls = sum(
        result.get("tool_calls", 0)
        for result in results
    )
    total_duration = sum(
        result.get("duration_seconds", 0)
        for result in results
    )
    return {
        "tasks": total,
        "passed": passed,
        "pass_rate": (
            passed / total
            if total
            else 0
        ),
        "avg_turns": (
            total_turns / total
            if total
            else 0
        ),
        "avg_tool_calls": (
            total_tool_calls / total
            if total
            else 0
        ),
        "avg_duration_seconds": (
            total_duration / total
            if total
            else 0
        ),
    }

def run_condition(
    tasks,
    client,
    enable_validation,
):
    results = []
    for index, task in enumerate(tasks, start=1):
        print(
            f"\n[{index}/{len(tasks)}] "
            f"{task['task_id']}"
        )
        result = run_task(
            task,
            client,
            enable_validation=enable_validation,
            enable_reviewer=False,
        )
        results.append(result)
        print(
            f"Passed: {result['passed']} | "
            f"Turns: {result.get('turns', 0)} | "
            f"Tools: {result.get('tool_calls', 0)} | "
            f"Duration: "
            f"{result.get('duration_seconds', 0):.2f}s"
        )

        time.sleep(5)

    return results


def print_comparison(off_summary, on_summary):
    print("\n")
    print("=" * 72)
    print("SELF-VALIDATION COMPARISON")
    print("=" * 72)

    print(
        f"{'Metric':<25}"
        f"{'Validation OFF':>20}"
        f"{'Validation ON':>20}"
    )

    print("-" * 72)

    print(
        f"{'Tasks':<25}"
        f"{off_summary['tasks']:>20}"
        f"{on_summary['tasks']:>20}"
    )

    print(
        f"{'Passed':<25}"
        f"{off_summary['passed']:>20}"
        f"{on_summary['passed']:>20}"
    )

    print(
        f"{'Pass rate':<25}"
        f"{off_summary['pass_rate'] * 100:>19.1f}%"
        f"{on_summary['pass_rate'] * 100:>19.1f}%"
    )

    print(
        f"{'Avg turns':<25}"
        f"{off_summary['avg_turns']:>20.2f}"
        f"{on_summary['avg_turns']:>20.2f}"
    )

    print(
        f"{'Avg tool calls':<25}"
        f"{off_summary['avg_tool_calls']:>20.2f}"
        f"{on_summary['avg_tool_calls']:>20.2f}"
    )

    print(
        f"{'Avg duration (s)':<25}"
        f"{off_summary['avg_duration_seconds']:>20.2f}"
        f"{on_summary['avg_duration_seconds']:>20.2f}"
    )

    print("=" * 72)


def main():
    tasks = load_tasks(TASKS_PATH)
    selected_task_ids = {
        "create_python_file",
        "fix_runtime_error",
        "modify_existing_function",
        "diagnose_program_failure",
    }
    tasks = [
        task
        for task in tasks
        if task["task_id"] in selected_task_ids
    ]
    print(f"Loaded {len(tasks)} evaluation tasks.")
    client = create_client()
    print("\n" + "=" * 72)
    print("RUN 1: VALIDATION OFF")
    print("=" * 72)
    off_results = run_condition(
        tasks,
        client,
        enable_validation=False,
    )
    print("\n" + "=" * 72)
    print("RUN 2: VALIDATION ON")
    print("=" * 72)
    on_results = run_condition(
        tasks,
        client,
        enable_validation=True,
    )

    off_summary = summarize(off_results)
    on_summary = summarize(on_results)

    print_comparison(
        off_summary,
        on_summary,
    )

    output = {
        "validation_off": {
            "summary": off_summary,
            "results": off_results,
        },
        "validation_on": {
            "summary": on_summary,
            "results": on_results,
        },
    }

    output_path = (
        Path(__file__).parent
        / "validation_comparison_results.json"
    )

    with open(
        output_path,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            output,
            file,
            indent=2,
        )

    print(f"\nResults written to: {output_path}")

if __name__ == "__main__":
    main()