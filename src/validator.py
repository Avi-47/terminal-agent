import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

@dataclass
class CheckResult:
    name: str
    passed: bool
    exit_code: int
    output: str

@dataclass
class ValidationResult:
    passed: bool
    checks: list[CheckResult]
    def to_text(self):
        lines = [
            "VALIDATION RESULT",
            f"Overall: {'PASS' if self.passed else 'FAIL'}",
            "",
        ]
        for check in self.checks:
            status = "PASS" if check.passed else "FAIL"
            lines.append(
                f"{check.name}: {status}"
            )
            lines.append(
                f"exit_code: {check.exit_code}"
            )
            if check.output:
                lines.append("output:")
                lines.append(check.output[-4000:])
            lines.append("")
        return "\n".join(lines)

def run_check(name, command, workspace):
    try:
        completed = subprocess.run(
            command,
            cwd=str(workspace),
            shell=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = (
            completed.stdout
            + "\n"
            + completed.stderr
        ).strip()
        return CheckResult(
            name=name,
            passed=completed.returncode == 0,
            exit_code=completed.returncode,
            output=output,
        )
    except subprocess.TimeoutExpired as error:
        return CheckResult(
            name=name,
            passed=False,
            exit_code=-1,
            output=f"Validation timed out: {error}",
        )
    except OSError as error:
        return CheckResult(
            name=name,
            passed=False,
            exit_code=-1,
            output=f"Validation could not start: {error}",
        )

def validate_workspace(workspace):
    workspace = Path(workspace)
    checks = []
    # Check 1: Python syntax / bytecode compilation.
    checks.append(
        run_check(
            "python_compile",
            [
                sys.executable,
                "-m",
                "compileall",
                "-q",
                ".",
            ],
            workspace,
        )
    )
    # Check 2: Project tests.
    checks.append(
        run_check(
            "pytest",
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
            ],
            workspace,
        )
    )
    return ValidationResult(
        passed=all(check.passed for check in checks),
        checks=checks,
    )