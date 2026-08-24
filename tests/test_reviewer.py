from unittest.mock import patch
from src.agent import Agent
from src.reviewer import parse_review_response

class FakeClient:
    pass

class PlanResponse:
    output = []
    output_text = (
        '{"needs_plan": false, "tasks": []}'
    )

class FinalResponse:
    output = []
    output_text = "Task completed."

class ApproveReviewResponse:
    output = []
    output_text = """
    {
        "decision": "APPROVE",
        "reason": "The requested work appears complete.",
        "revision_instructions": ""
    }
    """

class RejectReviewResponse:
    output = []
    output_text = """
    {
        "decision": "REJECT",
        "reason": "The requested change is incomplete.",
        "revision_instructions":
            "Complete the missing implementation and verify it."
    }
    """

# --------------------------------------------------
# Reviewer response parsing
# --------------------------------------------------

def test_parse_review_response_approve():
    result = parse_review_response(
        """
        {
            "decision": "APPROVE",
            "reason": "Looks correct.",
            "revision_instructions": ""
        }
        """
    )
    assert result["decision"] == "APPROVE"
    assert result["reason"] == "Looks correct."
    assert result["revision_instructions"] == ""

def test_parse_review_response_reject():
    result = parse_review_response(
        """
        {
            "decision": "REJECT",
            "reason": "Implementation is incomplete.",
            "revision_instructions": "Finish the implementation."
        }
        """
    )
    assert result["decision"] == "REJECT"
    assert result["reason"] == "Implementation is incomplete."
    assert (
        result["revision_instructions"]
        == "Finish the implementation."
    )

def test_parse_review_response_invalid_json_rejects():
    result = parse_review_response(
        "this is not valid json"
    )
    assert result["decision"] == "REJECT"
    assert result["revision_instructions"]

def test_parse_review_response_invalid_decision_rejects():
    result = parse_review_response(
        """
        {
            "decision": "MAYBE",
            "reason": "Unsure.",
            "revision_instructions": ""
        }
        """
    )
    assert result["decision"] == "REJECT"

def test_approve_clears_revision_instructions():
    result = parse_review_response(
        """
        {
            "decision": "APPROVE",
            "reason": "Correct.",
            "revision_instructions":
                "This should not be used."
        }
        """
    )
    assert result["decision"] == "APPROVE"
    assert result["revision_instructions"] == ""

# --------------------------------------------------
# Reviewer integration
# --------------------------------------------------

def test_reviewer_disabled_does_not_make_extra_model_call():
    agent = Agent(
        FakeClient(),
        enable_reviewer=False,
    )
    with patch(
        "src.agent.create_response",
        side_effect=[
            PlanResponse(),
            FinalResponse(),
        ],
    ) as mock_create_response:
        result = agent.run(
            "Say the task is complete."
        )
    assert result == "Task completed."
    assert mock_create_response.call_count == 2

def test_reviewer_approve_returns_primary_result():
    agent = Agent(
        FakeClient(),
        enable_reviewer=True,
    )
    with patch(
        "src.agent.create_response",
        side_effect=[
            PlanResponse(),
            FinalResponse(),
            ApproveReviewResponse(),
        ],
    ) as mock_create_response:
        result = agent.run(
            "Complete a simple task."
        )
    assert result == "Task completed."
    assert mock_create_response.call_count == 3

def test_reviewer_reject_triggers_one_revision_attempt():
    agent = Agent(
        FakeClient(),
        enable_reviewer=True,
    )
    with patch(
        "src.agent.create_response",
        side_effect=[
            # Initial attempt
            PlanResponse(),
            FinalResponse(),
            # Initial review
            RejectReviewResponse(),
            # Revision attempt
            PlanResponse(),
            FinalResponse(),
            # Final review
            ApproveReviewResponse(),
        ],
    ) as mock_create_response:
        result = agent.run(
            "Complete a task that needs correction."
        )
    assert result == "Task completed."
    # 2 calls for initial run
    # 1 call for initial review
    # 2 calls for revision
    # 1 call for final review
    assert mock_create_response.call_count == 6

def test_final_reject_stops_after_one_revision():
    agent = Agent(
        FakeClient(),
        enable_reviewer=True,
    )
    with patch(
        "src.agent.create_response",
        side_effect=[
            # Initial attempt
            PlanResponse(),
            FinalResponse(),
            # Initial review
            RejectReviewResponse(),
            # One revision attempt
            PlanResponse(),
            FinalResponse(),
            # Final review rejects again
            RejectReviewResponse(),
        ],
    ) as mock_create_response:
        result = agent.run(
            "Complete a task."
        )
    assert result == "Task completed."
    # Exactly one revision cycle.
    assert mock_create_response.call_count == 6