from pathlib import Path
from src.agent import Agent

def test_agent_accepts_stress_test_configuration():
    agent = Agent.__new__(Agent)
    agent.stress_test_config = None
    config = {
        "candidate_path": "solution.py",
        "reference_path": "reference.py",
        "generator_path": "generator.py",
        "trials": 20,
        "timeout": 5,
    }
    agent.configure_stress_test(config)
    assert agent.stress_test_config["candidate_path"] == "solution.py"
    assert agent.stress_test_config["reference_path"] == "reference.py"
    assert agent.stress_test_config["generator_path"] == "generator.py"
    assert agent.stress_test_config["trials"] == 20
    assert agent.stress_test_config["timeout"] == 5