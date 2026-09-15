import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class StressTestResult:
    passed: bool
    trials: int
    failed_trial: int | None = None
    input_data: str = ""
    candidate_output: str = ""
    reference_output: str = ""
    reason: str = ""

    def to_text(self):
        lines = [
            "STRESS TEST RESULT",
            f"Overall: {'PASS' if self.passed else 'FAIL'}",
            f"Trials: {self.trials}",
        ]

        if not self.passed:
            lines.extend([
                f"Failed trial: {self.failed_trial}",
                f"Reason: {self.reason}",
                "",
                "Input:",
                self.input_data,
                "",
                "Candidate output:",
                self.candidate_output,
                "",
                "Reference output:",
                self.reference_output,
            ])

        return "\n".join(lines)


def _run_python(
    script_path,
    input_data,
    workspace,
    timeout=5,
):
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
            ],
            input=input_data,
            capture_output=True,
            text=True,
            cwd=str(workspace),
            timeout=timeout,
            shell=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "output": "",
        }
    except OSError as error:
        return {
            "status": "error",
            "output": str(error),
        }

    if result.returncode != 0:
        return {
            "status": "runtime_error",
            "output": (
                result.stdout
                + "\n"
                + result.stderr
            ).strip(),
        }

    return {
        "status": "ok",
        "output": result.stdout,
    }


def _normalize_output(output):
    return " ".join(output.split())


def stress_test(
    workspace,
    candidate_path,
    reference_path,
    generator_path,
    trials=20,
    timeout=5,
):
    """
    Compare a candidate implementation against a
    deterministic reference implementation on generated
    test cases.

    The generator receives a seed on stdin and prints
    a valid test case to stdout.
    """

    workspace = Path(workspace).resolve()

    candidate = workspace / candidate_path
    reference = workspace / reference_path
    generator = workspace / generator_path

    for path in (
        candidate,
        reference,
        generator,
    ):
        if not path.is_file():
            return StressTestResult(
                passed=False,
                trials=0,
                reason=f"File not found: {path}",
            )

    for trial in range(trials):
        generator_result = _run_python(
            generator,
            str(trial),
            workspace,
            timeout=timeout,
        )

        if generator_result["status"] != "ok":
            return StressTestResult(
                passed=False,
                trials=trial,
                failed_trial=trial,
                reason=(
                    "Generator failed: "
                    f"{generator_result['status']}"
                ),
                input_data="",
                candidate_output="",
                reference_output=(
                    generator_result["output"]
                ),
            )

        input_data = generator_result["output"]

        candidate_result = _run_python(
            candidate,
            input_data,
            workspace,
            timeout=timeout,
        )

        if candidate_result["status"] != "ok":
            return StressTestResult(
                passed=False,
                trials=trial + 1,
                failed_trial=trial,
                input_data=input_data,
                candidate_output=(
                    candidate_result["output"]
                ),
                reference_output="",
                reason=(
                    "Candidate failed: "
                    f"{candidate_result['status']}"
                ),
            )

        reference_result = _run_python(
            reference,
            input_data,
            workspace,
            timeout=timeout,
        )

        if reference_result["status"] != "ok":
            return StressTestResult(
                passed=False,
                trials=trial + 1,
                failed_trial=trial,
                input_data=input_data,
                candidate_output="",
                reference_output=(
                    reference_result["output"]
                ),
                reason=(
                    "Reference failed: "
                    f"{reference_result['status']}"
                ),
            )

        candidate_output = _normalize_output(
            candidate_result["output"]
        )

        reference_output = _normalize_output(
            reference_result["output"]
        )

        if candidate_output != reference_output:
            return StressTestResult(
                passed=False,
                trials=trial + 1,
                failed_trial=trial,
                input_data=input_data,
                candidate_output=(
                    candidate_result["output"]
                ),
                reference_output=(
                    reference_result["output"]
                ),
                reason="Output mismatch",
            )

    return StressTestResult(
        passed=True,
        trials=trials,
    )