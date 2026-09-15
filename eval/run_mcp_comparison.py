import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agent import Agent
from .run_task import run_task


TASKS_PATH = (
    Path(__file__).resolve().parent /
    "mcp_tasks.json"
)


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


def load_tasks():
    with open(
        TASKS_PATH,
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def run_condition(
    tasks,
    client,
    enable_mcp,
):
    results = []

    condition_name = (
        "MCP ON"
        if enable_mcp
        else "MCP OFF"
    )

    for index, task in enumerate(
        tasks,
        start=1,
    ):
        print()
        print("=" * 72)
        print(
            f"{condition_name} | "
            f"Task {index}/{len(tasks)} | "
            f"{task['task_id']}"
        )
        print("=" * 72)

        result = run_task(
            task,
            client,
            use_repo_context=True,
            enable_validation=False,
            enable_reviewer=False,
            enable_mcp=enable_mcp,
        )

        results.append(result)

        print(
            f"Passed: {result['passed']} | "
            f"Turns: {result.get('turns', 0)} | "
            f"Tools: {result.get('tool_calls', 0)} | "
            f"Duration: "
            f"{result.get('duration_seconds', 0):.2f}s"
        )

        mcp_tools = [
            tool["name"]
            for tool in result.get("tools", [])
            if tool["name"].startswith("mcp_")
        ]

        if mcp_tools:
            print(
                f"MCP tools used: "
                f"{', '.join(mcp_tools)}"
            )
        else:
            print("MCP tools used: none")

        time.sleep(3)

    return results


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


def extract_mcp_tools(results):
    counts = {}

    for result in results:
        for tool in result.get("tools", []):
            name = tool.get("name", "")

            if name.startswith("mcp_"):
                counts[name] = (
                    counts.get(name, 0) + 1
                )

    return counts


def print_summary(
    name,
    results,
):
    summary = summarize(results)

    print()
    print("=" * 72)
    print(name)
    print("=" * 72)

    print(
        f"{'Tasks':<30}"
        f"{summary['tasks']:>15}"
    )

    print(
        f"{'Passed':<30}"
        f"{summary['passed']:>15}"
    )

    print(
        f"{'Pass rate':<30}"
        f"{summary['pass_rate'] * 100:>14.1f}%"
    )

    print(
        f"{'Average turns':<30}"
        f"{summary['avg_turns']:>15.2f}"
    )

    print(
        f"{'Average tool calls':<30}"
        f"{summary['avg_tool_calls']:>15.2f}"
    )

    print(
        f"{'Average duration (s)':<30}"
        f"{summary['avg_duration_seconds']:>15.2f}"
    )


def print_comparison(
    off_summary,
    on_summary,
):
    print()
    print("=" * 72)
    print("MCP EFFECTIVENESS COMPARISON")
    print("=" * 72)

    print(
        f"{'Metric':<30}"
        f"{'MCP OFF':>15}"
        f"{'MCP ON':>15}"
    )

    print("-" * 72)

    print(
        f"{'Tasks':<30}"
        f"{off_summary['tasks']:>15}"
        f"{on_summary['tasks']:>15}"
    )

    print(
        f"{'Passed':<30}"
        f"{off_summary['passed']:>15}"
        f"{on_summary['passed']:>15}"
    )

    print(
        f"{'Pass rate':<30}"
        f"{off_summary['pass_rate'] * 100:>14.1f}%"
        f"{on_summary['pass_rate'] * 100:>14.1f}%"
    )

    print(
        f"{'Average turns':<30}"
        f"{off_summary['avg_turns']:>15.2f}"
        f"{on_summary['avg_turns']:>15.2f}"
    )

    print(
        f"{'Average tool calls':<30}"
        f"{off_summary['avg_tool_calls']:>15.2f}"
        f"{on_summary['avg_tool_calls']:>15.2f}"
    )

    print(
        f"{'Average duration (s)':<30}"
        f"{off_summary['avg_duration_seconds']:>15.2f}"
        f"{on_summary['avg_duration_seconds']:>15.2f}"
    )

    print("=" * 72)


def main():
    tasks = load_tasks()

    print(
        f"Loaded {len(tasks)} MCP benchmark tasks."
    )

    client = create_client()

    print()
    print("=" * 72)
    print("RUN 1: MCP OFF")
    print("=" * 72)

    off_results = run_condition(
        tasks,
        client,
        enable_mcp=False,
    )

    print()
    print("=" * 72)
    print("RUN 2: MCP ON")
    print("=" * 72)

    on_results = run_condition(
        tasks,
        client,
        enable_mcp=True,
    )

    off_summary = summarize(
        off_results
    )

    on_summary = summarize(
        on_results
    )

    print_summary(
        "MCP OFF",
        off_results,
    )

    print_summary(
        "MCP ON",
        on_results,
    )

    print_comparison(
        off_summary,
        on_summary,
    )

    mcp_usage = extract_mcp_tools(
        on_results
    )

    print()
    print("=" * 72)
    print("MCP TOOL USAGE")
    print("=" * 72)

    if mcp_usage:
        for name, count in sorted(
            mcp_usage.items()
        ):
            print(
                f"{name}: {count}"
            )
    else:
        print("No MCP tools were used.")

    output = {
        "mcp_off": {
            "summary": off_summary,
            "results": off_results,
        },
        "mcp_on": {
            "summary": on_summary,
            "results": on_results,
        },
        "mcp_tool_usage": mcp_usage,
    }

    output_path = (
        Path(__file__).resolve().parent /
        "mcp_comparison_results.json"
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

    print()
    print(
        f"Results written to: {output_path}"
    )


if __name__ == "__main__":
    main()