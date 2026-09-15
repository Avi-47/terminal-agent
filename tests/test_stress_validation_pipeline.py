from src.validator import validate_workspace


def create_stress_workspace(tmp_path, candidate_code):
    (tmp_path / "solution.py").write_text(
        candidate_code,
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
import random
import sys

seed = int(sys.stdin.read().strip() or 0)
random.seed(seed)

numbers = [random.randint(-100, 100) for _ in range(10)]

print(*numbers)
""",
        encoding="utf-8",
    )

    (tmp_path / "test_solution.py").write_text(
        """
def test_solution_file_exists():
    from pathlib import Path
    assert Path("solution.py").exists()
""",
        encoding="utf-8",
    )


def test_validation_pipeline_stress_passes(tmp_path):
    create_stress_workspace(
        tmp_path,
        """
import sys

numbers = list(map(int, sys.stdin.read().split()))
print(sum(numbers))
""",
    )

    result = validate_workspace(
        tmp_path,
        stress_config={
            "candidate_path": "solution.py",
            "reference_path": "reference.py",
            "generator_path": "generator.py",
            "trials": 20,
            "timeout": 5,
        },
    )

    assert result.passed is True

    names = [check.name for check in result.checks]

    assert names == [
        "python_compile",
        "pytest",
        "stress_test",
    ]


def test_validation_pipeline_stress_fails(tmp_path):
    create_stress_workspace(
        tmp_path,
        """
import sys

numbers = list(map(int, sys.stdin.read().split()))
print(max(numbers))
""",
    )

    result = validate_workspace(
        tmp_path,
        stress_config={
            "candidate_path": "solution.py",
            "reference_path": "reference.py",
            "generator_path": "generator.py",
            "trials": 20,
            "timeout": 5,
        },
    )

    assert result.passed is False

    stress_check = result.checks[-1]

    assert stress_check.name == "stress_test"
    assert stress_check.passed is False
    assert "Output mismatch" in stress_check.output
    assert "Candidate output:" in stress_check.output
    assert "Reference output:" in stress_check.output