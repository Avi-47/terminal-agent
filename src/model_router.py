# MODELS = [
#     "qwen/qwen3.6-27b",
#     "openai/gpt-oss-120b",
#     "openai/gpt-oss-20b",
#     "llama-3.3-70b-versatile",
#     "llama-3.1-8b-instant",
# ]
MODELS = [
    # "gemini-2.5-flash",
    "gemini-3.6-flash",
]

def create_response(client, models, instructions, conversation, tools):
    last_error = None

    for model in models:
        try:
            print(f"\n[Model: {model}]")

            # return client.responses.create(
            #     model=model,
            #     instructions=instructions,
            #     input=conversation,
            #     tools=tools,
            # )
            client.chat.completions.create(
                model=model,
                messages=conversation,
                tools=tools,
            )

        except Exception as e:
            if "429" not in str(e):
                raise

            print(f"\n[Rate limit] {model} unavailable.")
            last_error = e

    raise RuntimeError(
        "All configured models are currently rate-limited."
    ) from last_error