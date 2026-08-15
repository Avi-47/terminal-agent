from model_router import MODELS, create_response
from tools import TOOLS, execute_tool_call


class Agent:
    def __init__(self, client):
        self.client = client
        self.conversation = []
        self.max_iterations = 10

        self.instructions = (
            "You are a helpful coding assistant. "
            "Only use tools that are explicitly provided to you. "
            "Do not invent or request tools that are not available. "
            "If you need information that available tools cannot provide, "
            "explain the limitation instead. "

            "For simple requests, act directly without unnecessary planning. "

            "For any multi-step coding task, before making the first tool call, "
            "output a short section beginning exactly with 'Plan:' followed by "
            "the main steps you intend to perform. Do not begin tool execution "
            "until the plan has been stated. Keep the plan concise and focused. "

            "When working with an unfamiliar project or file, inspect the "
            "workspace or relevant files before modifying them. Do not inspect "
            "the workspace unnecessarily when the requested file and operation "
            "are already clear. "

            "When a dedicated tool exists for an operation, use that dedicated "
            "tool instead of attempting the same operation through run_command. "
            "In particular, when Git information is needed, use git_status "
            "instead of running Git commands through run_command. "

            "After modifying code, normally run an appropriate command to "
            "verify that the change works. "

            "Treat tool errors, non-zero exit codes, stderr output, exceptions, "
            "and other execution failures as observations that can be used to "
            "diagnose a problem. A failed tool execution does not automatically "
            "mean the task has failed. "

            "When an execution failure is recoverable, diagnose the cause before "
            "retrying. Inspect the relevant code or error information, make an "
            "appropriate correction, and run the verification again. Do not "
            "blindly repeat the same failing tool call. "

            "After a successful verification that satisfies the user's request, "
            "stop making unnecessary changes or repeated verification calls. "

            "Do not claim that a coding task is complete until you have "
            "performed appropriate verification when verification is possible."
        )

    def run(self, prompt):
        self.conversation.append({
            "role": "user",
            "content": prompt,
        })

        response = create_response(
            self.client,
            MODELS,
            self.instructions,
            self.conversation,
            TOOLS,
        )

        iteration = 0

        while True:
            if iteration >= self.max_iterations:
                print(
                    "\nAgent stopped: "
                    "maximum tool iterations reached."
                )
                return response.output_text

            iteration += 1

            tool_outputs = []

            # Save the model's response into the conversation.
            self.conversation.extend(response.output)

            # Show any model text that accompanies tool calls.
            has_tool_calls = any(
                item.type == "function_call"
                for item in response.output
            )

            if has_tool_calls and response.output_text.strip():
                print("\nAgent >")
                print(response.output_text)

            for item in response.output:

                if item.type != "function_call":
                    continue

                print(f"\nTool requested: {item.name}")
                print(f"Arguments: {item.arguments}")
                print(f"Call ID: {item.call_id}")

                tool_result = execute_tool_call(
                    item.name,
                    item.arguments,
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
                return response.output_text

            # Save tool results into conversation.
            self.conversation.extend(tool_outputs)

            # Ask the model what to do next.
            response = create_response(
                self.client,
                MODELS,
                self.instructions,
                self.conversation,
                TOOLS,
            )