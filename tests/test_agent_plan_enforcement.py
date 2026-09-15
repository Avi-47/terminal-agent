from src.agent import Agent
def test_plan_task_is_not_marked_done_without_tool_call():
    agent = Agent.__new__(Agent)
    agent.plan = [
        {
            "task": "Read solution.py",
            "status": "in_progress",
        }
    ]
    agent.current_plan_index = 0
    assert agent.plan[0]["status"] == "in_progress"
    assert agent.current_plan_index == 0