import ast
import re
from pathlib import Path

IGNORED_DIRECTORIES = {
    ".git",
    ".pytest_cache",
    "__pycache__",
}

def tokenize_query(query):
    """
    Convert a user query into lowercase searchable terms.
    Returns unique terms while preserving their original order.
    """
    if not isinstance(query, str):
        raise ValueError(
            "query must be a string"
        )
    terms = re.findall(
        r"[a-zA-Z0-9_]+",
        query.lower(),
    )
    seen = set()
    unique_terms = []
    for term in terms:
        if term not in seen:
            seen.add(term)
            unique_terms.append(term)
    return unique_terms

def should_ignore(path: Path) -> bool:
    """
    Return True if a path contains a directory that should not
    be included in repository context.
    """
    return any(
        part in IGNORED_DIRECTORIES
        for part in path.parts
    )

def format_repository_context(entries, max_files=3, max_characters=2000,):
    """
    Format retrieved repository entries into a bounded
    context block for the agent.
    """
    if not isinstance(entries, list):
        raise ValueError(
            "entries must be a list"
        )
    if not isinstance(max_files, int):
        raise ValueError(
            "max_files must be an integer"
        )
    if max_files < 1:
        raise ValueError(
            "max_files must be at least 1"
        )
    if not isinstance(max_characters, int):
        raise ValueError(
            "max_characters must be an integer"
        )
    if max_characters < 1:
        raise ValueError(
            "max_characters must be at least 1"
        )
    if not entries:
        return ""
    sections = []
    for entry in entries[:max_files]:
        lines = [
            f"File: {entry['path']}",
        ]
        if entry["classes"]:
            lines.append(
                "Classes: "
                + ", ".join(entry["classes"])
            )
        if entry["functions"]:
            lines.append(
                "Functions: "
                + ", ".join(entry["functions"])
            )
        section = "\n".join(lines)
        sections.append(section)
    context = (
        "RELEVANT REPOSITORY CONTEXT:\n\n"
        + "\n\n".join(sections)
    )
    return context[:max_characters]

def retrieve_relevant_files(repository_map,query,top_k=3,):
    """
    Return the most relevant repository entries for a user query.
    Entries with a score of zero are excluded.
    """
    if not isinstance(repository_map, list):
        raise ValueError(
            "repository_map must be a list"
        )
    if not isinstance(top_k, int):
        raise ValueError(
            "top_k must be an integer"
        )
    if top_k < 1:
        raise ValueError(
            "top_k must be at least 1"
        )
    query_terms = tokenize_query(query)
    scored_entries = []
    for entry in repository_map:
        score = score_repository_entry(
            entry,
            query_terms,
        )
        if score > 0:
            scored_entries.append(
                {
                    **entry,
                    "score": score,
                }
            )
    scored_entries.sort(
        key=lambda item: (
            -item["score"],
            item["path"].lower(),
        )
    )
    return scored_entries[:top_k]

def score_repository_entry(entry, query_terms):
    """
    Score one repository map entry against query terms.
    A term can match:
        - the file path
        - a class name
        - a function name
    Returns an integer relevance score.
    """
    path = entry["path"].lower()
    classes = [
        name.lower()
        for name in entry["classes"]
    ]
    functions = [
        name.lower()
        for name in entry["functions"]
    ]
    score = 0
    for term in query_terms:
        if term in path:
            score += 1
        if any(term in name for name in classes):
            score += 1
        if any(term in name for name in functions):
            score += 1
    return score

def extract_python_symbols(file_path: Path):
    """
    Extract top-level classes and functions from a Python file.
    Returns a dictionary with:
        classes
        functions
    """
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (
        OSError,
        UnicodeDecodeError,
        SyntaxError,
    ):
        return {
            "classes": [],
            "functions": [],
        }
    classes = []
    functions = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            functions.append(node.name)

    return {
        "classes": classes,
        "functions": functions,
    }

import re


def find_relevant_files(repo_context, prompt, limit=5):
    """
    Return repository files ranked by relevance to the user's request.
    """
    if not isinstance(repo_context, list):
        return []

    if not isinstance(prompt, str) or not prompt.strip():
        return []

    prompt_text = prompt.lower()

    prompt_words = set(
        re.findall(
            r"[a-zA-Z0-9_]+",
            prompt_text,
        )
    )

    scored_files = []

    for item in repo_context:
        if not isinstance(item, dict):
            continue

        score = 0

        path = item.get("path", "")

        if isinstance(path, str):
            path_lower = path.lower()

            # Strong match if the filename/path appears directly
            # in the user's request.
            if path_lower in prompt_text:
                score += 10

            path_words = set(
                re.findall(
                    r"[a-zA-Z0-9_]+",
                    path_lower.replace("/", " "),
                )
            )

            for word in prompt_words:
                if word in path_words:
                    score += 3

        for key in ("classes", "functions"):
            symbols = item.get(key, [])

            if not isinstance(symbols, list):
                continue

            for symbol in symbols:
                if not isinstance(symbol, str):
                    continue

                symbol_lower = symbol.lower()

                # Exact symbol match.
                if symbol_lower in prompt_text:
                    score += 10

                # Also support partial token matches.
                symbol_words = set(
                    re.findall(
                        r"[a-zA-Z0-9]+",
                        symbol_lower.replace("_", " "),
                    )
                )

                for word in prompt_words:
                    if word in symbol_words:
                        score += 5

        if score > 0:
            scored_files.append({
                **item,
                "score": score,
            })

    scored_files.sort(
        key=lambda item: (
            -item["score"],
            item.get("path", ""),
        )
    )
    return scored_files[:limit]

def build_repository_map(workspace_root):
    """
    Scan the workspace and build a lightweight map of Python files
    and their top-level symbols.
    Returns a list of dictionaries.
    """
    workspace_root = Path(workspace_root).resolve()
    if not workspace_root.exists():
        raise ValueError(
            f"workspace does not exist: {workspace_root}"
        )
    if not workspace_root.is_dir():
        raise ValueError(
            f"workspace is not a directory: {workspace_root}"
        )
    repository_map = []
    for file_path in workspace_root.rglob("*.py"):
        relative_path = file_path.relative_to(
            workspace_root
        )
        if should_ignore(relative_path):
            continue
        symbols = extract_python_symbols(file_path)
        repository_map.append(
            {
                "path": relative_path.as_posix(),
                "classes": symbols["classes"],
                "functions": symbols["functions"],
            }
        )
    return sorted(
        repository_map,
        key=lambda item: item["path"].lower(),
    )