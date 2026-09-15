from pathlib import Path

from src.stress_tester import stress_test


def test_stress_test_passes():
    workspace = Path("tests") / "stress_workspace"
    workspace.mkdir(
        parents=True,
        exist_ok=True,
    )

    candidate = workspace / "candidate.py"
    reference = workspace / "reference.py"
    generator = workspace / "generator.py"

    candidate.write_text(
    """
import sys

numbers = list(map(int, sys.stdin.read().split()))
print(sum(numbers))
""",
    encoding="utf-8",
)

    reference.write_text(
        """
import sys

numbers = list(map(int, sys.stdin.read().split()))
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

    result = stress_test(
        workspace=workspace,
        candidate_path="candidate.py",
        reference_path="reference.py",
        generator_path="generator.py",
        trials=10,
    )

    assert result.passed is True
    assert result.trials == 10