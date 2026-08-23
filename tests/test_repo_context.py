from src.repo_context import (
    build_repository_map,
    extract_python_symbols,
    find_relevant_files,
    format_repository_context,
    retrieve_relevant_files,
    score_repository_entry,
    tokenize_query,
)

def test_tokenize_query():
    result = tokenize_query(
        "Fix the Model fallback logic!"
    )
    assert result == [
        "fix",
        "the",
        "model",
        "fallback",
        "logic",
    ]

def test_tokenize_query_removes_duplicates():
    result = tokenize_query(
        "model model fallback model"
    )
    assert result == [
        "model",
        "fallback",
    ]

def test_score_repository_entry():
    entry = {
        "path": "src/model_router.py",
        "classes": ["ModelRouter"],
        "functions": [
            "create_response",
            "fallback_model",
        ],
    }
    score = score_repository_entry(
        entry,
        ["model", "fallback"],
    )
    assert score == 4

def test_retrieve_relevant_files_respects_top_k():
    repository_map = [
        {
            "path": "src/a.py",
            "classes": [],
            "functions": ["model"],
        },
        {
            "path": "src/b.py",
            "classes": [],
            "functions": ["model"],
        },
        {
            "path": "src/c.py",
            "classes": [],
            "functions": ["model"],
        },
    ]
    results = retrieve_relevant_files(
        repository_map,
        "model",
        top_k=2,
    )
    assert len(results) == 2



def test_retrieve_relevant_files_uses_deterministic_order():
    repository_map = [
        {
            "path": "src/tools.py",
            "classes": [],
            "functions": [
                "model_tool",
            ],
        },
        {
            "path": "src/agent.py",
            "classes": [],
            "functions": [
                "model_agent",
            ],
        },
    ]
    results = retrieve_relevant_files(
        repository_map,
        "model",
        top_k=2,
    )
    assert [
        item["path"]
        for item in results
    ] == [
        "src/agent.py",
        "src/tools.py",
    ]

def test_format_repository_context_empty():
    result = format_repository_context([])
    assert result == ""

def test_format_repository_context_respects_character_limit():
    entries = [
        {
            "path": "src/very_long_file.py",
            "classes": ["VeryLongClassName"],
            "functions": [
                "very_long_function_name",
                "another_long_function_name",
            ],
            "score": 1,
        }
    ]
    result = format_repository_context(
        entries,
        max_characters=50,
    )
    assert len(result) == 50

def test_format_repository_context_respects_max_files():
    entries = [
        {
            "path": "src/a.py",
            "classes": [],
            "functions": ["a"],
            "score": 3,
        },
        {
            "path": "src/b.py",
            "classes": [],
            "functions": ["b"],
            "score": 2,
        },
    ]
    result = format_repository_context(
        entries,
        max_files=1,
    )
    assert "src/a.py" in result
    assert "src/b.py" not in result

def test_format_repository_context():
    entries = [
        {
            "path": "src/agent.py",
            "classes": ["Agent"],
            "functions": [
                "run",
                "create_plan",
            ],
            "score": 3,
        }
    ]
    result = format_repository_context(entries)

    assert result == (
        "RELEVANT REPOSITORY CONTEXT:\n\n"
        "File: src/agent.py\n"
        "Classes: Agent\n"
        "Functions: run, create_plan"
    )

def test_retrieve_relevant_files_ranks_entries():
    repository_map = [
        {
            "path": "src/tools.py",
            "classes": [],
            "functions": [
                "read_file",
                "write_file",
            ],
        },
        {
            "path": "src/model_router.py",
            "classes": ["ModelRouter"],
            "functions": [
                "fallback_model",
            ],
        },
        {
            "path": "src/agent.py",
            "classes": ["Agent"],
            "functions": [
                "run",
            ],
        },
    ]
    results = retrieve_relevant_files(
        repository_map,
        "fix model fallback",
        top_k=2,
    )
    assert len(results) == 1
    assert results[0]["path"] == (
        "src/model_router.py"
    )
    assert results[0]["score"] == 4

def test_extract_python_symbols(tmp_path):
    file_path = tmp_path / "example.py"
    file_path.write_text(
        """
class User:
    pass

def hello():
    return "hello"

async def fetch_data():
    return []
""",
        encoding="utf-8",
    )
    result = extract_python_symbols(file_path)
    assert result["classes"] == ["User"]
    assert result["functions"] == [
        "hello",
        "fetch_data",
    ]

def test_extract_python_symbols_handles_invalid_python(
    tmp_path,
):
    file_path = tmp_path / "broken.py"
    file_path.write_text(
        "def broken(:",
        encoding="utf-8",
    )
    result = extract_python_symbols(file_path)
    assert result == {
        "classes": [],
        "functions": [],
    }

def test_build_repository_map(tmp_path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    agent_file = src_dir / "agent.py"
    agent_file.write_text(
        """
class Agent:
    pass

def run():
    pass
""",
        encoding="utf-8",
    )
    result = build_repository_map(tmp_path)
    assert result == [
        {
            "path": "src/agent.py",
            "classes": ["Agent"],
            "functions": ["run"],
        }
    ]

def test_repository_map_ignores_pycache(tmp_path):
    cache_dir = tmp_path / "__pycache__"
    cache_dir.mkdir()
    cached_file = cache_dir / "ignored.py"
    cached_file.write_text(
        "def should_not_appear(): pass",
        encoding="utf-8",
    )
    result = build_repository_map(tmp_path)
    assert result == []

def test_find_relevant_files_prioritizes_matching_function():
    context = [
        {
            "path": "src/tools.py",
            "classes": [],
            "functions": [
                "validate_command",
                "read_file",
            ],
        },
        {
            "path": "src/model_router.py",
            "classes": [],
            "functions": [
                "create_response",
            ],
        },
    ]

    results = find_relevant_files(
        context,
        "Find validate_command",
    )

    assert results[0]["path"] == "src/tools.py"

def test_find_relevant_files_prioritizes_matching_path():
    context = [
        {
            "path": "src/tools.py",
            "classes": [],
            "functions": [],
        },
        {
            "path": "src/model_router.py",
            "classes": [],
            "functions": [],
        },
    ]

    results = find_relevant_files(
        context,
        "Inspect the tools implementation",
    )

    assert results[0]["path"] == "src/tools.py"