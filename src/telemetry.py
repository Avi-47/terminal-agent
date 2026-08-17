import json
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path


LOG_DIR = Path("logs")
RUN_LOG = LOG_DIR / "runs.jsonl"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def redact(value):
    """Remove obvious secrets from telemetry."""
    if value is None:
        return value

    text = str(value)

    patterns = [
        (r"(?i)(api[_-]?key\s*[=:]\s*)[^\s,;]+", r"\1[REDACTED]"),
        (r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s]+", r"\1[REDACTED]"),
        (r"(?i)(password\s*[=:]\s*)[^\s,;]+", r"\1[REDACTED]"),
        (r"(?i)(secret\s*[=:]\s*)[^\s,;]+", r"\1[REDACTED]"),
        (r"(?i)(token\s*[=:]\s*)[^\s,;]+", r"\1[REDACTED]"),
    ]

    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)

    return text


class RunTelemetry:
    def __init__(self, model=None):
        self.data = {
            "run_id": str(uuid.uuid4()),
            "started_at": utc_now(),
            "finished_at": None,
            "model": model,
            "turns": 0,
            "tool_calls": 0,
            "status": "running",
            "duration_seconds": None,
            "model_calls": [],
            "tools": [],
        }

        self._started = time.perf_counter()

    def record_model_call(
        self,
        turn,
        duration,
        response=None,
    ):
        usage = getattr(response, "usage", None)

        input_tokens = None
        output_tokens = None

        if usage is not None:
            input_tokens = getattr(
                usage,
                "input_tokens",
                getattr(usage, "prompt_tokens", None),
            )
            output_tokens = getattr(
                usage,
                "output_tokens",
                getattr(usage, "completion_tokens", None),
            )

        self.data["turns"] += 1

        self.data["model_calls"].append({
            "turn": turn,
            "duration_seconds": round(duration, 6),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        })

    def record_tool_call(
        self,
        name,
        duration,
        success,
    ):
        self.data["tool_calls"] += 1

        self.data["tools"].append({
            "name": name,
            "duration_seconds": round(duration, 6),
            "status": "success" if success else "error",
        })

    def finish(self, status="success", error=None):
        self.data["finished_at"] = utc_now()
        self.data["duration_seconds"] = round(
            time.perf_counter() - self._started,
            6,
        )
        self.data["status"] = status

        if error is not None:
            self.data["error_type"] = type(error).__name__
            self.data["error_message"] = redact(error)

        self.persist()

    def persist(self):
        LOG_DIR.mkdir(parents=True, exist_ok=True)

        with RUN_LOG.open(
            "a",
            encoding="utf-8",
        ) as file:
            file.write(
                json.dumps(
                    self.data,
                    ensure_ascii=False,
                )
                + "\n"
            )

    def summary(self):
        return (
            "\nRun complete.\n"
            f"Model: {self.data['model']}\n"
            f"Turns: {self.data['turns']}\n"
            f"Tool calls: {self.data['tool_calls']}\n"
            f"Duration: {self.data['duration_seconds']:.2f}s\n"
            f"Status: {self.data['status']}\n"
        )