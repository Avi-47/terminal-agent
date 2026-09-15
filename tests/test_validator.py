from pathlib import Path
from src.validator import (
    CheckResult,
    ValidationResult,
    run_stress_test_check,
)

def test_stress_test_check_passes(tmp_path):
    candidate = tmp_path / "candidate.py"
    reference = tmp_path / "reference.py"
    generator = tmp_path / "generator.py"
    candidate.write_text(
        """
import sys
numbers = list(
    map(int, sys.stdin.read().split())
)
print(sum(numbers))
""",
        encoding="utf-8",
    )
    reference.write_text(
        """
import sys
numbers = list(
    map(int, sys.stdin.read().split())
)
total = 0
for number in numbers:
    total += number
print(total)
""",
        encoding="utf-8",
    )
    generator.write_text(
        """
import random
import sys
seed = int(sys.stdin.read())
random.seed(seed)
numbers = [
    random.randint(-100, 100)
    for _ in range(10)
]
print(*numbers)
""",
        encoding="utf-8",
    )
    result = run_stress_test_check(
        workspace=Path(tmp_path),
        candidate_path="candidate.py",
        reference_path="reference.py",
        generator_path="generator.py",
        trials=5,
    )
    assert result.passed is True
    assert result.name == "stress_test"
    assert result.exit_code == 0

def test_stress_test_check_fails(tmp_path):
    candidate = tmp_path / "candidate.py"
    reference = tmp_path / "reference.py"
    generator = tmp_path / "generator.py"

    candidate.write_text(
        """
import sys

numbers = list(
    map(int, sys.stdin.read().split())
)

print(max(numbers))
""",
        encoding="utf-8",
    )

    reference.write_text(
        """
import sys

numbers = list(
    map(int, sys.stdin.read().split())
)

print(sum(numbers))
""",
        encoding="utf-8",
    )

    generator.write_text(
        """
import random
import sys

seed = int(sys.stdin.read())
random.seed(seed)

numbers = [
    random.randint(-100, 100)
    for _ in range(10)
]

print(*numbers)
""",
        encoding="utf-8",
    )

    result = run_stress_test_check(
        workspace=Path(tmp_path),
        candidate_path="candidate.py",
        reference_path="reference.py",
        generator_path="generator.py",
        trials=5,
    )

    assert result.passed is False
    assert result.name == "stress_test"
    assert result.exit_code == 1
    assert "Output mismatch" in result.output

def test_validate_workspace_without_stress_testing(tmp_path):
    from src.validator import validate_workspace
    result = validate_workspace(tmp_path)
    assert len(result.checks) == 2
    names = [
        check.name
        for check in result.checks
    ]
    assert names == [
        "python_compile",
        "pytest",
    ]

def test_check_result_passes():
    result = CheckResult(
        name="pytest",
        passed=True,
        exit_code=0,
        output="10 passed",
    )
    assert result.passed is True
    assert result.exit_code == 0

def test_validation_result_passes_when_all_checks_pass():
    result = ValidationResult(
        passed=True,
        checks=[
            CheckResult(
                name="compile",
                passed=True,
                exit_code=0,
                output="",
            ),
            CheckResult(
                name="pytest",
                passed=True,
                exit_code=0,
                output="10 passed",
            ),
        ],
    )
    assert result.passed is True
    assert "Overall: PASS" in result.to_text()

def test_validation_result_fails_when_one_check_fails():
    result = ValidationResult(
        passed=False,
        checks=[
            CheckResult(
                name="compile",
                passed=True,
                exit_code=0,
                output="",
            ),
            CheckResult(
                name="pytest",
                passed=False,
                exit_code=1,
                output="2 failed",
            ),
        ],
    )

    assert result.passed is False
    assert "Overall: FAIL" in result.to_text()
    assert "2 failed" in result.to_text()