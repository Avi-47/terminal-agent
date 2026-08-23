from eval.run_repo_context_comparison import (
    load_repo_context_tasks,
)

def test_load_repo_context_tasks():
    tasks = load_repo_context_tasks()
    assert len(tasks) == 3
    for task in tasks:
        assert task["task_id"].startswith(
            "repo_context_"
        )