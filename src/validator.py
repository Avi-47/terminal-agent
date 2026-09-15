from .stress_tester import stress_test
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

def run_stress_test_check(workspace, candidate_path, reference_path, generator_path, trials=20, timeout=5,):
    result = stress_test(
        workspace=workspace,
        candidate_path=candidate_path,
        reference_path=reference_path,
        generator_path=generator_path,
        trials=trials,
        timeout=timeout,
    )

    return CheckResult(
        name="stress_test",
        passed=result.passed,
        exit_code=0 if result.passed else 1,
        output=result.to_text(),
    )

def validate_workspace(workspace, stress_config=None):
    workspace = Path(workspace)
    checks = []

    compile_check = run_check(
        "python_compile",
        [sys.executable, "-m", "compileall", "-q", "."],
        workspace,
    )
    checks.append(compile_check)

    if not compile_check.passed:
        return ValidationResult(
            passed=False,
            checks=checks,
        )

    pytest_check = run_check(
        "pytest",
        [sys.executable, "-m", "pytest", "-q"],
        workspace,
    )
    checks.append(pytest_check)

    if not pytest_check.passed:
        return ValidationResult(
            passed=False,
            checks=checks,
        )

    if stress_config is not None:
        checks.append(
            run_stress_test_check(
                workspace=workspace,
                candidate_path=stress_config["candidate_path"],
                reference_path=stress_config["reference_path"],
                generator_path=stress_config["generator_path"],
                trials=stress_config.get("trials", 20),
                timeout=stress_config.get("timeout", 5),
            )
        )

    return ValidationResult(
        passed=all(check.passed for check in checks),
        checks=checks,
    )