from pathlib import Path
from eval.results import calculate_summary
from eval.run import create_client
from eval.run_task import run_task
from eval.tasks import load_tasks

BASE_DIR = Path(__file__).resolve().parent.parent
TASKS_PATH = BASE_DIR / "eval" / "tasks.json"

def load_repo_context_tasks():
    tasks = load_tasks(TASKS_PATH)
    return [
        task
        for task in tasks
        if task["task_id"].startswith("repo_context_")
    ]

def run_variant(tasks, client, use_repo_context):
    results = []
    for task in tasks:
        result = run_task(
            task,
            client,
            use_repo_context=use_repo_context,
        )
        results.append(result)
    return results

def run_comparison():
    tasks = load_repo_context_tasks()
    if not tasks:
        raise RuntimeError(
            "No repository-context evaluation tasks found."
        )
    client = create_client()
    print("Running repository context comparison...\n")
    print("Context OFF")
    baseline_results = run_variant(
        tasks,
        client,
        use_repo_context=False,
    )
    print("\nContext ON")
    context_results = run_variant(
        tasks,
        client,
        use_repo_context=True,
    )
    baseline_summary = calculate_summary(
        baseline_results
    )
    context_summary = calculate_summary(
        context_results
    )
    print("\nComparison")
    print("----------")
    print(
        f"Context OFF pass rate: "
        f"{baseline_summary['pass_rate']:.1f}%"
    )
    print(
        f"Context ON pass rate:  "
        f"{context_summary['pass_rate']:.1f}%"
    )
    print(
        f"\nContext OFF avg turns: "
        f"{baseline_summary['average_turns']:.1f}"
    )
    print(
        f"Context ON avg turns:  "
        f"{context_summary['average_turns']:.1f}"
    )
    print(
        f"\nContext OFF avg tool calls: "
        f"{baseline_summary['average_tool_calls']:.1f}"
    )
    print(
        f"Context ON avg tool calls:  "
        f"{context_summary['average_tool_calls']:.1f}"
    )
    print(
        f"\nContext OFF avg duration: "
        f"{baseline_summary['average_duration']:.1f}s"
    )
    print(
        f"Context ON avg duration:  "
        f"{context_summary['average_duration']:.1f}s"
    )
    return {
        "context_off": baseline_results,
        "context_on": context_results,
        "context_off_summary": baseline_summary,
        "context_on_summary": context_summary,
    }

if __name__ == "__main__":
    run_comparison()