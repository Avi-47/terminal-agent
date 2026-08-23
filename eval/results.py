import json
from pathlib import Path

def write_result(path, result):
    path = Path(path)
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    with open(
        path,
        "a",
        encoding="utf-8",
    ) as file:
        json.dump(
            result,
            file,
            ensure_ascii=False,
        )
        file.write("\n")

def calculate_summary(results):
    total = len(results)

    if total == 0:
        return {
            "total_tasks": 0,
            "passed_tasks": 0,
            "pass_rate": 0.0,
            "average_turns": 0.0,
            "average_tool_calls": 0.0,
            "average_duration": 0.0,
        }

    passed = sum(
        1
        for result in results
        if result.get("passed") is True
    )

    turns = [
        result["turns"]
        for result in results
        if "turns" in result
    ]

    tool_calls = [
        result["tool_calls"]
        for result in results
        if "tool_calls" in result
    ]

    durations = [
        result["duration_seconds"]
        for result in results
        if "duration_seconds" in result
    ]

    return {
        "total_tasks": total,
        "passed_tasks": passed,
        "pass_rate": passed / total * 100,
        "average_turns": (
            sum(turns) / len(turns)
            if turns
            else 0.0
        ),
        "average_tool_calls": (
            sum(tool_calls) / len(tool_calls)
            if tool_calls
            else 0.0
        ),
        "average_duration": (
            sum(durations) / len(durations)
            if durations
            else 0.0
        ),
    }