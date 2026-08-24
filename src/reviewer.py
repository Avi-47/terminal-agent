import json


REVIEW_INSTRUCTIONS = """
You are an independent code reviewer.

Your job is to review the result produced by a coding agent.

You are NOT the coding agent.
You must not attempt to solve the task yourself.
You must evaluate the evidence provided to you.

Review the following:

1. Did the changes appear relevant to the user's request?
2. Do the changes appear to satisfy the requested task?
3. Are there obvious regressions, contradictions, or incomplete work?
4. Is there evidence that the implementation should be rejected?

Return ONLY a JSON object.

Do not use Markdown.
Do not use code fences.
Do not write any text before or after the JSON.

The JSON must have exactly this structure:

{
  "decision": "APPROVE",
  "reason": "short explanation",
  "revision_instructions": ""
}

or:

{
  "decision": "REJECT",
  "reason": "short explanation",
  "revision_instructions": "clear instructions for the coding agent"
}

Rules:

- Use APPROVE when the available evidence reasonably shows that
  the user's request was completed correctly.
- Use REJECT when the implementation appears incomplete, incorrect,
  irrelevant, contradictory, or obviously broken.
- Do not reject solely because you wish the implementation had been
  done differently.
- Do not invent problems that are not supported by the evidence.
- If APPROVE, revision_instructions must be an empty string.
- If REJECT, revision_instructions must clearly explain what should
  be corrected.
"""


def parse_review_response(raw):
    """
    Parse and validate the reviewer's structured JSON response.
    """

    raw = raw.strip()

    if raw.startswith("```"):
        lines = raw.splitlines()

        if lines:
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        raw = "\n".join(lines).strip()

    try:
        data = json.loads(raw)

    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")

        if start == -1 or end == -1 or end < start:
            return {
                "decision": "REJECT",
                "reason": (
                    "Reviewer returned an invalid structured response."
                ),
                "revision_instructions": (
                    "Inspect the completed work and verify that the "
                    "original request has been fully satisfied."
                ),
            }

        try:
            data = json.loads(
                raw[start:end + 1]
            )
        except json.JSONDecodeError:
            return {
                "decision": "REJECT",
                "reason": (
                    "Reviewer returned an invalid structured response."
                ),
                "revision_instructions": (
                    "Inspect the completed work and verify that the "
                    "original request has been fully satisfied."
                ),
            }

    if not isinstance(data, dict):
        return {
            "decision": "REJECT",
            "reason": (
                "Reviewer returned an invalid structured response."
            ),
            "revision_instructions": (
                "Inspect the completed work and verify that the "
                "original request has been fully satisfied."
            ),
        }

    decision = data.get("decision")
    reason = data.get("reason", "")
    revision_instructions = data.get(
        "revision_instructions",
        "",
    )

    if decision not in (
        "APPROVE",
        "REJECT",
    ):
        return {
            "decision": "REJECT",
            "reason": (
                "Reviewer returned an unsupported review decision."
            ),
            "revision_instructions": (
                "Inspect the completed work and verify that the "
                "original request has been fully satisfied."
            ),
        }

    if not isinstance(reason, str):
        reason = ""

    if not isinstance(
        revision_instructions,
        str,
    ):
        revision_instructions = ""

    if decision == "APPROVE":
        revision_instructions = ""

    return {
        "decision": decision,
        "reason": reason,
        "revision_instructions": revision_instructions,
    }