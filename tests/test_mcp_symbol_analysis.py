from pathlib import Path

from src.repo_context import analyze_symbol


def test_analyze_symbol_finds_definition():
    result = analyze_symbol(
        Path.cwd(),
        "validate_workspace",
    )

    assert result["symbol"] == "validate_workspace"
    assert result["definitions"]

    files = {
        item["file"]
        for item in result["definitions"]
    }

    assert "src/agent.py" in files


def test_analyze_symbol_finds_references():
    result = analyze_symbol(
        Path.cwd(),
        "validate_workspace",
    )

    assert result["references"]


def test_analyze_symbol_unknown_symbol():
    result = analyze_symbol(
        Path.cwd(),
        "symbol_that_does_not_exist",
    )

    assert result["definitions"] == []
    assert result["references"] == []