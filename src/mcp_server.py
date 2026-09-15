import os
from pathlib import Path
from mcp.server import MCPServer
from repo_context import (
    build_repository_map,
    retrieve_relevant_files,
    format_repository_context,
)

mcp = MCPServer("terminal-agent")
WORKSPACE_ROOT = Path(
    os.environ.get(
        "TERMINAL_AGENT_WORKSPACE",
        Path(__file__).resolve().parent.parent,
    )
).resolve()

@mcp.tool()
def repository_summary() -> str:
    """Return a summary of the Python files and symbols in the repository."""
    repository_map = build_repository_map(WORKSPACE_ROOT)
    file_count = len(repository_map)
    class_count = sum(
        len(entry["classes"])
        for entry in repository_map
    )
    function_count = sum(
        len(entry["functions"])
        for entry in repository_map
    )
    return (
        f"Repository root: {WORKSPACE_ROOT}\n"
        f"Python files: {file_count}\n"
        f"Classes: {class_count}\n"
        f"Functions: {function_count}"
    )

@mcp.tool()
def search_repository(query: str, limit: int = 5) -> str:
    """
    Search the repository for files relevant to a query.
    Returns a bounded repository-context summary containing
    matching files, classes, and functions.
    """
    if not isinstance(query, str) or not query.strip():
        return "Query must be a non-empty string."
    if not isinstance(limit, int):
        return "Limit must be an integer."
    if limit < 1:
        return "Limit must be at least 1."
    repository_map = build_repository_map(WORKSPACE_ROOT)
    relevant_files = retrieve_relevant_files(
        repository_map,
        query,
        top_k=limit,
    )
    if not relevant_files:
        return f"No relevant files found for query: {query}"
    return format_repository_context(
        relevant_files,
        max_files=limit,
        max_characters=4000,
    )

if __name__ == "__main__":
    mcp.run()