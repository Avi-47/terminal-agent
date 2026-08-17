import json
import re

from src.telemetry import RunTelemetry


def test_run_creation():
    telemetry = RunTelemetry(model="test-model")

    assert telemetry.data["run_id"]
    assert telemetry.data["model"] == "test-model"
    assert telemetry.data["turns"] == 0
    assert telemetry.data["tool_calls"] == 0
    assert telemetry.data["status"] == "running"
    assert telemetry.data["finished_at"] is None


def test_model_call_recording():
    telemetry = RunTelemetry(model="test-model")

    telemetry.record_model_call(
        turn=1,
        duration=0.123,
    )

    assert telemetry.data["turns"] == 1
    assert len(telemetry.data["model_calls"]) == 1
    assert telemetry.data["model_calls"][0]["turn"] == 1
    assert telemetry.data["model_calls"][0]["duration_seconds"] == 0.123


def test_tool_call_recording():
    telemetry = RunTelemetry(model="test-model")

    telemetry.record_tool_call(
        "read_file",
        0.003,
        True,
    )

    assert telemetry.data["tool_calls"] == 1
    assert telemetry.data["tools"][0] == {
        "name": "read_file",
        "duration_seconds": 0.003,
        "status": "success",
    }


def test_failed_tool_recording():
    telemetry = RunTelemetry(model="test-model")

    telemetry.record_tool_call(
        "run_command",
        0.12,
        False,
    )

    assert telemetry.data["tools"][0]["status"] == "error"


def test_run_completion():
    telemetry = RunTelemetry(model="test-model")

    telemetry.finish()

    assert telemetry.data["status"] == "success"
    assert telemetry.data["finished_at"] is not None
    assert telemetry.data["duration_seconds"] >= 0


def test_error_recording():
    telemetry = RunTelemetry(model="test-model")

    error = ValueError("something failed")

    telemetry.finish(
        status="error",
        error=error,
    )

    assert telemetry.data["status"] == "error"
    assert telemetry.data["error_type"] == "ValueError"
    assert telemetry.data["error_message"] == "something failed"


def test_jsonl_persistence(tmp_path, monkeypatch):
    import src.telemetry as telemetry_module

    monkeypatch.setattr(
        telemetry_module,
        "LOG_DIR",
        tmp_path,
    )

    monkeypatch.setattr(
        telemetry_module,
        "RUN_LOG",
        tmp_path / "runs.jsonl",
    )

    telemetry = RunTelemetry(model="test-model")
    telemetry.record_tool_call(
        "read_file",
        0.01,
        True,
    )
    telemetry.finish()

    log_file = tmp_path / "runs.jsonl"

    assert log_file.exists()

    lines = log_file.read_text(
        encoding="utf-8",
    ).splitlines()

    assert len(lines) == 1

    data = json.loads(lines[0])

    assert data["model"] == "test-model"
    assert data["status"] == "success"
    assert data["tool_calls"] == 1


def test_secret_redaction(tmp_path, monkeypatch):
    import src.telemetry as telemetry_module

    monkeypatch.setattr(
        telemetry_module,
        "LOG_DIR",
        tmp_path,
    )

    monkeypatch.setattr(
        telemetry_module,
        "RUN_LOG",
        tmp_path / "runs.jsonl",
    )

    telemetry = RunTelemetry(model="test-model")

    error = ValueError(
        "api_key=SUPER_SECRET_VALUE"
    )

    telemetry.finish(
        status="error",
        error=error,
    )

    contents = (
        tmp_path / "runs.jsonl"
    ).read_text(
        encoding="utf-8",
    )

    assert "SUPER_SECRET_VALUE" not in contents
    assert "[REDACTED]" in contents


def test_telemetry_does_not_store_tool_arguments():
    telemetry = RunTelemetry(model="test-model")

    telemetry.record_tool_call(
        "read_file",
        0.01,
        True,
    )

    data = telemetry.data

    assert "arguments" not in data["tools"][0]
    assert "result" not in data["tools"][0]