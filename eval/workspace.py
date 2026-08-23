import tempfile
from pathlib import Path

def create_workspace(setup):
    workspace = Path(
        tempfile.mkdtemp(prefix="terminal-agent-eval-")
    )
    try:
        files = setup.get("files", {})
        if not isinstance(files, dict):
            raise ValueError(
                "setup.files must be an object"
            )
        for relative_path, content in files.items():
            if not isinstance(relative_path, str):
                raise ValueError(
                    "setup file path must be a string"
                )
            if not isinstance(content, str):
                raise ValueError(
                    "setup file content must be a string"
                )
            file_path = _safe_path(
                workspace,
                relative_path,
            )
            if file_path is None:
                raise ValueError(
                    f"setup path is outside workspace: "
                    f"{relative_path}"
                )
            file_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            file_path.write_text(
                content,
                encoding="utf-8",
            )
        return workspace
    except Exception:
        cleanup_workspace(workspace)
        raise

def _safe_path(workspace, relative_path):
    workspace = Path(workspace).resolve()
    candidate = (
        workspace / relative_path
    ).resolve()
    try:
        candidate.relative_to(workspace)
    except ValueError:
        return None
    return candidate

def cleanup_workspace(workspace):
    workspace = Path(workspace)
    if not workspace.exists():
        return
    import shutil
    shutil.rmtree(workspace)