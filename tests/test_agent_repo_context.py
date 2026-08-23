from src.agent import Agent

def test_agent_builds_targeted_repo_context(tmp_path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    tools_file = src_dir / "tools.py"
    tools_file.write_text(
        """
def validate_command(args):
    return None
""",
        encoding="utf-8",
    )
    agent = Agent(
        client=None,
        workspace=tmp_path,
        use_repo_context=True,
    )
    context = agent.get_repo_context_instruction(
        "Find validate_command"
    )
    assert "src/tools.py" in context
    assert "validate_command" in context

def test_agent_can_disable_repo_context(tmp_path):
    agent = Agent(
        client=None,
        workspace=tmp_path,
        use_repo_context=False,
    )
    context = agent.get_repo_context_instruction(
        "Find validate_command"
    )
    assert context == ""

def test_agent_repo_context_prioritizes_relevant_file(
    tmp_path,
):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    tools_file = src_dir / "tools.py"
    router_file = src_dir / "model_router.py"
    tools_file.write_text(
        """
def validate_command(args):
    return None
""",
        encoding="utf-8",
    )
    router_file.write_text(
        """
def create_response():
    return None
""",
        encoding="utf-8",
    )
    agent = Agent(
        client=None,
        workspace=tmp_path,
        use_repo_context=True,
    )
    context = agent.get_repo_context_instruction(
        "Find validate_command"
    )
    assert "src/tools.py" in context

def test_agent_builds_repository_context(tmp_path):
    source_file = tmp_path / "model_router.py"
    source_file.write_text(
        """
def fallback_model():
    pass

def create_response():
    pass
""",
        encoding="utf-8",
    )
    agent = Agent(
        client=None,
        workspace=tmp_path,
    )
    context = agent.build_repository_context(
        "Fix the model fallback logic"
    )
    assert "RELEVANT REPOSITORY CONTEXT:" in context
    assert "model_router.py" in context
    assert "fallback_model" in context

def test_agent_returns_empty_context_when_no_match(tmp_path,):
    source_file = tmp_path / "tools.py"
    source_file.write_text(
        """
def read_file():
    pass
""",
        encoding="utf-8",
    )
    agent = Agent(
        client=None,
        workspace=tmp_path,
    )
    context = agent.build_repository_context(
        "completely unrelated quantum banana"
    )
    assert context == ""

def test_repository_context_flag_defaults_and_can_be_disabled():
    agent = Agent(
        client=None,
    )
    assert agent.use_repo_context is True
    disabled_agent = Agent(
        client=None,
        use_repo_context=False,
    )
    assert disabled_agent.use_repo_context is False