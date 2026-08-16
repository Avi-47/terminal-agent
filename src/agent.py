import json
from .model_router import MODELS, create_response
from .tools import TOOLS, execute_tool_call


class Agent:
    def __init__(self, client):
        self.client = client
        self.conversation = []
        self.max_iterations = 10
        self.plan = []
        self.current_plan_index = 0

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

            "When the user asks you to search, find, locate, or look for text "
            "inside the project or codebase, use search_files. Do not use "
            "run_command for codebase searching. "

            "When a dedicated tool exists for an operation, use that dedicated "
            "tool instead of attempting the same operation through run_command. "
            "In particular, when Git information is needed, use git_status "
            "instead of running Git commands through run_command. "

            "After modifying code, normally run an appropriate command to "
            "verify that the change works. "
            "When running Python tests, use 'python -m pytest' rather than "
            "'pytest' directly. "

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

    def create_plan(self, prompt):
        planning_instructions = (
            "You are a planning component for a coding agent. "
            "Decide whether the user's request requires a multi-step plan. "

            "Return ONLY valid JSON. Do not use Markdown. "
            "Do not include explanations. "

            "The JSON must have exactly this structure: "
            '{"needs_plan": true, "tasks": [{"task": "..."}, {"task": "..."}]} '

            "If the request is simple and does not need multiple steps, return: "
            '{"needs_plan": false, "tasks": []} '

            "If a plan is needed, create concise, concrete tasks. "
            "Each task should represent one meaningful step of the user's request. "
            "Do not include status fields. "
            "The Python agent will add and manage task status."
        )
        planning_conversation = [
            {
                "role": "user",
                "content": prompt,
            }
        ]
        response = create_response(
            self.client,
            MODELS,
            planning_instructions,
            planning_conversation,
            [],
        )
        raw = response.output_text.strip()
        if raw.startswith("```"):
            raw = raw.removeprefix("```json").removeprefix("```")
            raw = raw.removesuffix("```").strip()
        plan_data = json.loads(raw)
        if not plan_data.get("needs_plan"):
            return []
        tasks = plan_data.get("tasks", [])
        return [
            {
                "task": item["task"],
                "status": "pending",
            }
            for item in tasks
        ]

    def display_plan(self):
        if not self.plan:
            return

        print("\nPlan:")

        for item in self.plan:
            status = item["status"]
            task = item["task"]

            if status == "pending":
                symbol = "[ ]"
            elif status == "in_progress":
                symbol = "[>]"
            elif status == "done":
                symbol = "[x]"
            else:
                symbol = "[?]"

            print(f"{symbol} {task}")

    def display_plan_item(self, index):
        if not self.plan:
            return

        if index < 0 or index >= len(self.plan):
            return
        item = self.plan[index]
        status = item["status"]
        task = item["task"]
        if status == "pending":
            symbol = "[ ]"
        elif status == "in_progress":
            symbol = "[>]"
        elif status == "done":
            symbol = "[x]"
        else:
            symbol = "[?]"
        print(f"{symbol} {task}")
    
    def update_plan_status(self, index, status):
        if not self.plan:
            return

        if status not in ("pending", "in_progress", "done"):
            raise ValueError(f"Invalid plan status: {status}")

        if index < 0 or index >= len(self.plan):
            raise IndexError("Plan index out of range")

        self.plan[index]["status"] = status

    def start_plan_task(self, index):
        if not self.plan:
            return
        self.update_plan_status(index, "in_progress")
        self.display_plan_item(index)

    def finish_plan_task(self, index):
        if not self.plan:
            return
        self.update_plan_status(index, "done")
        self.display_plan_item(index)

    def run(self, prompt):
        self.plan = self.create_plan(prompt)
        self.current_plan_index = 0

        # Show the complete plan once.
        self.display_plan()

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

            # Save model response.
            self.conversation.extend(response.output)

            # Show model text accompanying tool calls.
            has_tool_calls = any(
                item.type == "function_call"
                for item in response.output
            )

            if has_tool_calls and response.output_text.strip():
                print("\nAgent >")
                print(response.output_text)

            # Start the current plan task.
            if (
                self.plan
                and self.current_plan_index < len(self.plan)
            ):
                self.start_plan_task(self.current_plan_index)

            for item in response.output:

                if item.type != "function_call":
                    continue

                print(f"\nTool requested: {item.name}")

                tool_result = execute_tool_call(
                    item.name,
                    item.arguments,
                )

                print("\nTool completed successfully.")

                tool_outputs.append({
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": tool_result,
                })

            # If there were no tool calls, the model has finished.
            if not tool_outputs:

                # Finish only the task that was actually started.
                if (
                    self.plan
                    and self.current_plan_index < len(self.plan)
                    and self.plan[self.current_plan_index]["status"]
                    == "in_progress"
                ):
                    self.finish_plan_task(self.current_plan_index)
                    self.current_plan_index += 1

                return response.output_text

            # The current task's tool work is complete.
            if (
                self.plan
                and self.current_plan_index < len(self.plan)
            ):
                self.finish_plan_task(self.current_plan_index)
                self.current_plan_index += 1

            # Save tool results.
            self.conversation.extend(tool_outputs)

            # Ask the model what to do next.
            response = create_response(
                self.client,
                MODELS,
                self.instructions,
                self.conversation,
                TOOLS,
            )