from src.validator import validate_workspace


def create_workspace_with_bug(tmp_path):
    (tmp_path / "solution.py").write_text(
        """
import sys

numbers = list(map(int, sys.stdin.read().split()))
print(max(numbers))
""",
        encoding="utf-8",
    )

    (tmp_path / "reference.py").write_text(
        """
import sys

numbers = list(map(int, sys.stdin.read().split()))
print(sum(numbers))
""",
        encoding="utf-8",
    )

    (tmp_path / "generator.py").write_text(
        """
import sys

print("1 2 3 4")
""",
        encoding="utf-8",
    )

    (tmp_path / "test_solution.py").write_text(
        """
from pathlib import Path


def test_solution_exists():
    assert Path("solution.py").exists()
""",
        encoding="utf-8",
    )


def test_stress_failure_contains_counterexample(tmp_path):
    create_workspace_with_bug(tmp_path)

    result = validate_workspace(
        tmp_path,
        stress_config={
            "candidate_path": "solution.py",
            "reference_path": "reference.py",
            "generator_path": "generator.py",
            "trials": 1,
            "timeout": 5,
        },
    )

    assert result.passed is False

    stress_check = result.checks[-1]

    assert stress_check.name == "stress_test"
    assert stress_check.passed is False

    output = stress_check.output

    assert "Input:" in output
    assert "Candidate output:" in output
    assert "Reference output:" in output
    assert "Output mismatch" in output