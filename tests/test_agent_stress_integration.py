from pathlib import Path
from src.agent import Agent

def test_agent_stress_test_defaults_to_disabled():
    agent = Agent.__new__(Agent)
    agent.stress_test_config = None
    assert agent.stress_test_config is None

def test_agent_configure_stress_test():
    agent = Agent.__new__(Agent)
    agent.stress_test_config = None
    config = {
        "candidate_path": "solution.py",
        "reference_path": "reference.py",
        "generator_path": "generator.py",
        "trials": 10,
        "timeout": 3,
    }
    agent.configure_stress_test(config)
    assert agent.stress_test_config == config

def test_agent_configure_stress_test_rejects_missing_fields():
    agent = Agent.__new__(Agent)
    agent.stress_test_config = None
    try:
        agent.configure_stress_test({
            "candidate_path": "solution.py",
        })
    except ValueError:
        return
    assert False, "Expected ValueError"