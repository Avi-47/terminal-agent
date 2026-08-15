import os

from dotenv import load_dotenv
from openai import OpenAI

from tools import TOOLS, execute_tool_call


def main():
    load_dotenv()

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        print("Error: GROQ_API_KEY is not set.")
        return

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
    )

    conversation = []

    instructions = (
        "You are a helpful coding assistant. "
        "Only use tools that are explicitly provided to you. "
        "Do not invent or request tools that are not available. "
        "If you need information that available tools cannot provide, "
        "explain the limitation instead."
    )

    print("Terminal Agent")
    print("Type 'exit' or 'quit' to leave.\n")

    while True:
        try:
            prompt = input("You > ")

        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        prompt = prompt.strip()

        if not prompt:
            continue

        if prompt.lower() in ("exit", "quit"):
            print("Goodbye!")
            break

        conversation.append({
            "role": "user",
            "content": prompt
        })

        try:
            response = client.responses.create(
                model="openai/gpt-oss-20b",
                instructions=instructions,
                input=conversation,
                tools=TOOLS,
            )

            max_iterations = 10
            iteration = 0

            while True:

                if iteration >= max_iterations:
                    print(
                        "\nAgent stopped: "
                        "maximum tool iterations reached."
                    )
                    break

                iteration += 1

                tool_outputs = []

                # Save the model's response into the conversation.
                conversation.extend(response.output)

                for item in response.output:

                    if item.type != "function_call":
                        continue

                    print(f"\nTool requested: {item.name}")
                    print(f"Arguments: {item.arguments}")
                    print(f"Call ID: {item.call_id}")

                    tool_result = execute_tool_call(
                        item.name,
                        item.arguments
                    )

                    print("\nTool result:")
                    print(tool_result)

                    tool_outputs.append({
                        "type": "function_call_output",
                        "call_id": item.call_id,
                        "output": tool_result,
                    })

                # No tool calls means the model has finished.
                if not tool_outputs:
                    print("\nAgent >")
                    print(response.output_text)
                    break

                # Save tool results into conversation.
                conversation.extend(tool_outputs)

                # Ask the model what to do next.
                response = client.responses.create(
                    model="openai/gpt-oss-20b",
                    instructions=instructions,
                    input=conversation,
                    tools=TOOLS,
                )

            print()

        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()