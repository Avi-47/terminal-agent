import os

from dotenv import load_dotenv
# from openai import OpenAI
from google import genai
from .agent import Agent

def main():
    load_dotenv()

    # api_key = os.getenv("GROQ_API_KEY")
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        # print("Error: GROQ_API_KEY is not set.")
        print("Error: GEMINI_API_KEY is not set.")
        return

    # client = OpenAI(
    #     api_key=api_key,
    #     # base_url="https://api.groq.com/openai/v1",
    #     base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    # )
    client = genai.Client(api_key=api_key)

    agent = Agent(client)

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

        try:
            result = agent.run(prompt)

            print("\nAgent >")
            print(result)
            print()

        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()