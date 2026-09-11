MODELS = [
    "qwen/qwen3.6-27b",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    # "llama-3.3-70b-versatile",
    # "llama-3.1-8b-instant",
]
# MODELS = [
#     # "gemini-2.5-flash",
#     "gemini-3.6-flash",
# ]

def create_response(
    client,
    models,
    instructions,
    conversation,
    tools,
):
    last_error = None

    for model in models:
        try:
            print(f"\n[Model: {model}]")

            return client.responses.create(
                model=model,
                instructions=instructions,
                input=conversation,
                tools=tools,
            )

        except Exception as error:
            last_error = error
            error_text = str(error).lower()

            retryable = (
                "429" in error_text
                or "rate_limit_exceeded" in error_text
                or "too many requests" in error_text
                or "tokens per minute" in error_text
            )

            if retryable:
                print(
                    f"\n[Rate limit] {model} unavailable. "
                    "Trying next model."
                )
                continue

            raise

    raise RuntimeError(
        "All configured models are currently unavailable."
    ) from last_error