from src.validator import (
    CheckResult,
    ValidationResult,
)


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