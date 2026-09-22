from pathlib import Path
from src.agent import Agent
class DummyClient:
    pass

def test_mcp_client_closes_after_agent_run():
    agent = Agent(
        DummyClient(),
        workspace=Path.cwd(),
        enable_mcp=True,
        enable_reviewer=False,
    )
    original_run = agent._run
    try:
        agent._run = lambda prompt: "test result"
        result = agent.run(
            "test MCP cleanup"
        )
        assert result == "test result"
        assert agent.mcp_client is None
        assert agent.mcp_tools == []
        assert agent.mcp_tool_names == set()
    finally:
        agent._run = original_run
        agent.stop_mcp()