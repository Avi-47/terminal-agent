from src.telemetry import RunTelemetry
from pathlib import Path
from src.agent import Agent

class DummyClient:
    pass
def test_mcp_tools_are_discovered():
    agent = Agent(
        DummyClient(),
        workspace=Path.cwd(),
        enable_mcp=True,
    )
    try:
        agent.start_mcp()
        names = {
            tool["name"]
            for tool in agent.mcp_tools
        }
        assert "mcp_repository_summary" in names
        assert "mcp_search_repository" in names
    finally:
        agent.stop_mcp()

def test_mcp_search_repository_dispatch():
    agent = Agent(
        DummyClient(),
        workspace=Path.cwd(),
        enable_mcp=True,
    )
    agent.telemetry = RunTelemetry()
    try:
        agent.start_mcp()
        result = agent._execute_tool_with_telemetry(
            "mcp_search_repository",
            {
                "query": "validation",
                "limit": 3,
            },
        )
        assert "RELEVANT REPOSITORY CONTEXT" in result
    finally:
        agent.stop_mcp()