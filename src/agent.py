import json
import time

from .model_router import MODELS, create_response
from . import tools
from .tools import (TOOLS,execute_tool_call,set_workspace_root,)
from .telemetry import RunTelemetry
from .repo_context import (
    build_repository_map,
    retrieve_relevant_files,
    format_repository_context,
    find_relevant_files,
)
class Agent:
    def __init__(
        self,
        client,
        confirm_callback=None,
        workspace=None,
        use_repo_context=True,
    ):
        self.client = client

        if workspace is not None:
            set_workspace_root(workspace)

        self.confirm_callback = confirm_callback
        self.commit_confirmed = False
        self.conversation = []
        self.max_iterations = 10

        self.use_repo_context = use_repo_context

        # ALWAYS initialize this
        self.repo_context = []

        # Only build repository context when a workspace exists
        if self.use_repo_context and workspace is not None:
            try:
                self.repo_context = build_repository_map(
                    workspace
                )
            except (OSError, ValueError):
                self.repo_context = []

        self.plan = []
        self.current_plan_index = 0

        self.repository_context = ""
        self.repository_top_k = 3
        self.repository_context_max_characters = 2000

        self.instructions = (
            "You are a helpful coding assistant. "
            "Only use tools that are explicitly provided to you. "
            "Do not invent or request tools that are not available. "
            "If you need information that available tools cannot provide, "
            "explain the limitation instead. "

            "For each plan step, complete the actual action described by that step "
            "before moving to the next step. Tool calls are not automatically equivalent "
            "to completing a plan step. For example, list_files does not complete a "
            "'read file' step, and read_file does not complete a 'modify file' step. "
            "If a plan step says to modify or create a file, you must actually call "
            "write_file with the required complete contents. "
            "If a plan step says to verify a program, you must actually run the "
            "appropriate verification command. "
            "Do not claim or assume a plan step is complete merely because a related "
            "tool call succeeded. "

            "When the requested file path is already known, use read_file directly. "
            "Do not use list_files merely to confirm that a known file exists. "
            "Use list_files only when the relevant file or directory is unknown. "

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
            "run_command for codebase searching. After receiving search results, "
            "summarize the relevant matches in your final response, including the "
            "file path when the user asks where something is located. "

            "When a dedicated tool exists for an operation, use that dedicated "
            "tool instead of attempting the same operation through run_command. "
            "For Git operations, use the dedicated Git tools instead of "
            "run_command. Use git_status to inspect which files are modified, "
            "staged, or untracked. Use git_diff to inspect the actual content "
            "of unstaged changes. Use git_add only when the user explicitly "
            "asks to stage changes. Use git_commit only when the user explicitly "
            "asks to create a commit. Never automatically stage or commit changes "
            "just because a coding task has been completed. Do not request Git "
            "commands that are not provided as dedicated tools. "

            "Do not use git_status alone when the user asks what the actual "
            "content of a change is. In that situation, use git_diff. "
            
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

            "When a task requires creating or modifying a file, do not use list_files "
            "as a substitute for the modification. After inspecting the file if needed, "
            "you MUST call write_file with the complete intended file contents. "
            "For an existing-file modification, the normal sequence is: "
            "read_file -> determine the corrected contents -> write_file -> verify. "
            "Do not stop after read_file. Do not report completion until write_file "
            "has returned successfully. "

            "When a file path is explicitly known, do not call list_files before "
            "read_file. "
            "After read_file on an existing-file modification, you must call "
            "write_file with the complete corrected file contents. "
            "After write_file succeeds, run an appropriate verification command "
            "when possible. "
        )

    def request_commit_confirmation(self):
        if self.confirm_callback is None:
            return False

        confirmed = self.confirm_callback()
        self.commit_confirmed = bool(confirmed)
        return self.commit_confirmed

    def get_workspace_root(self):
        return tools.WORKSPACE_ROOT

    def build_repository_context(self, prompt):
        """
        Build lightweight repository context relevant to the user request.
        """
        repository_map = build_repository_map(
            self.get_workspace_root()
        )
        relevant_entries = retrieve_relevant_files(
            repository_map,
            prompt,
            top_k=self.repository_top_k,
        )
        return format_repository_context(
            relevant_entries,
            max_files=self.repository_top_k,
            max_characters=(
                self.repository_context_max_characters
            ),
        )

    def confirm_commit(self):
        self.commit_confirmed = True

    def revoke_commit_confirmation(self):
        self.commit_confirmed = False

    def get_model_name(self):
        if isinstance(MODELS, (list, tuple)):
            if MODELS:
                return MODELS[0]

        return str(MODELS)

    def get_repo_context_instruction(self, prompt):
        """
        Build targeted repository context for the current user request.
        """
        if not self.use_repo_context:
            return ""

        if not self.repo_context:
            return ""

        relevant_files = find_relevant_files(
            self.repo_context,
            prompt,
        )

        if not relevant_files:
            return ""

        context_lines = []

        for item in relevant_files:
            path = item.get("path", "")
            classes = item.get("classes", [])
            functions = item.get("functions", [])

            context_lines.append(
                {
                    "path": path,
                    "classes": classes,
                    "functions": functions,
                }
            )

        return (
            "\n\nRELEVANT REPOSITORY CONTEXT:\n"
            + json.dumps(
                context_lines,
                indent=2,
            )
            + "\n\n"
            + (
                "The repository context above identifies files that are likely "
                "relevant to the user's request. Use it to guide exploration. "
                "When a specific relevant file is strongly indicated, prefer "
                "read_file on that file instead of unnecessarily searching the "
                "entire codebase. Repository context is a hint, not a substitute "
                "for inspecting file contents before modifying code."
            )
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
        model_started = time.perf_counter()

        try:
            response = create_response(
                self.client,
                MODELS,
                planning_instructions,
                planning_conversation,
                [],
            )
        except Exception:
            model_duration = time.perf_counter() - model_started

            if hasattr(self, "telemetry") and self.telemetry:
                self.telemetry.record_model_call(
                    turn=self.telemetry.data["turns"] + 1,
                    duration=model_duration,
                )

            raise

        model_duration = time.perf_counter() - model_started

        if hasattr(self, "telemetry") and self.telemetry:
            self.telemetry.record_model_call(
                turn=self.telemetry.data["turns"] + 1,
                duration=model_duration,
                response=response,
            )
        raw = response.output_text.strip()
        if raw.startswith("```"):
            raw = raw.removeprefix("```json").removeprefix("```")
            raw = raw.removesuffix("```").strip()
        try:
            plan_data = json.loads(raw)
        except json.JSONDecodeError:
            return []
        if not isinstance(plan_data, dict):
            return []
        if not plan_data.get("needs_plan"):
            return []
        tasks = plan_data.get("tasks", [])
        if not isinstance(tasks, list):
            return []
        return [
            {
                "task": item["task"],
                "status": "pending",
            }
            for item in tasks
            if isinstance(item, dict) and isinstance(item.get("task"), str)
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

    def get_current_plan_instruction(self):
        if not self.plan:
            return ""
        if self.current_plan_index >= len(self.plan):
            return ""
        task = self.plan[self.current_plan_index]["task"]
        return (
            "\nCURRENT PLAN TASK:\n"
            f"{task}\n"
            "\nComplete this task before moving to the next plan task. "
            "Do not treat an unrelated tool call as completion of this task. "
        )

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
        self.telemetry = RunTelemetry(
            model=self.get_model_name(),
        )

        try:
            result = self._run(prompt)

            self.telemetry.finish(status="success")
            print(self.telemetry.summary())

            return result

        except Exception as error:
            self.telemetry.finish(
                status="error",
                error=error,
            )
            print(self.telemetry.summary())
            raise

    def _run(self, prompt):
        self.repository_context = (
            self.build_repository_context(prompt)
        )
        repo_context_instruction = (
            self.get_repo_context_instruction(prompt)
        )
        self.plan = self.create_plan(prompt)
        self.current_plan_index = 0

        # Show the complete plan once.
        self.display_plan()

        self.conversation.append({
            "role": "user",
            "content": prompt,
        })

        # Initial/main model call.
        model_started = time.perf_counter()

        try:
            response = create_response(
                self.client,
                MODELS,
                (
                    self.instructions
                    + repo_context_instruction
                    + self.get_current_plan_instruction()
                ),
                self.conversation,
                TOOLS,
            )
        except Exception:
            model_duration = time.perf_counter() - model_started
            self.telemetry.record_model_call(
                turn=self.telemetry.data["turns"] + 1,
                duration=model_duration,
            )
            raise
        model_duration = time.perf_counter() - model_started
        self.telemetry.record_model_call(
            turn=self.telemetry.data["turns"] + 1,
            duration=model_duration,
            response=response,
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
                # Commit requires explicit confirmation.
                if item.name == "git_commit" and not self.commit_confirmed:
                    if self.confirm_callback is not None:
                        self.commit_confirmed = bool(
                            self.confirm_callback()
                        )
                    if not self.commit_confirmed:
                        tool_result = (
                            "Error: git commit requires explicit confirmation "
                            "after the agent asks for confirmation."
                        )
                        # Record the blocked commit as an error.
                        self.telemetry.record_tool_call(
                            item.name,
                            0.0,
                            False,
                        )
                    else:
                        tool_result = self._execute_tool_with_telemetry(
                            item.name,
                            item.arguments,
                        )
                else:
                    tool_result = self._execute_tool_with_telemetry(
                        item.name,
                        item.arguments,
                    )
                if (
                    tool_result.startswith("Error:")
                    or tool_result.startswith("Unknown tool:")
                ):
                    print("\nTool rejected or failed.")
                else:
                    print("\nTool completed successfully.")
                tool_outputs.append({
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": tool_result,
                })
            # If there were no tool calls, check if tasks remain.
            if not tool_outputs:
                if (
                    self.plan
                    and self.current_plan_index < len(self.plan)
                    and self.plan[self.current_plan_index]["status"]
                    == "in_progress"
                ):
                    self.finish_plan_task(self.current_plan_index)
                    self.current_plan_index += 1
                
                # Only return if no more tasks remain
                if not self.plan or self.current_plan_index >= len(self.plan):
                    return response.output_text
                
                # Otherwise, ask the model to continue with the next task
                model_started = time.perf_counter()
                try:
                    response = create_response(
                        self.client,
                        MODELS,
                        self.get_model_instructions(),
                        self.conversation,
                        TOOLS,
                    )
                except Exception:
                    model_duration = time.perf_counter() - model_started
                    self.telemetry.record_model_call(
                        turn=self.telemetry.data["turns"] + 1,
                        duration=model_duration,
                    )
                    raise
                model_duration = time.perf_counter() - model_started
                self.telemetry.record_model_call(
                    turn=self.telemetry.data["turns"] + 1,
                    duration=model_duration,
                    response=response,
                )
                continue
            # Save tool results.
            self.conversation.extend(tool_outputs)
            # Ask the model what to do next.
            model_started = time.perf_counter()
            try:
                response = create_response(
                    self.client,
                    MODELS,
                    self.get_model_instructions(),
                    self.conversation,
                    TOOLS,
                )
            except Exception:
                model_duration = time.perf_counter() - model_started
                self.telemetry.record_model_call(
                    turn=self.telemetry.data["turns"] + 1,
                    duration=model_duration,
                )
                raise
            model_duration = time.perf_counter() - model_started
            self.telemetry.record_model_call(
                turn=self.telemetry.data["turns"] + 1,
                duration=model_duration,
                response=response,
            )

    def get_model_instructions(self):
        parts = [
            self.instructions,
        ]
        if self.repository_context:
            parts.append(
                "\n"
                + self.repository_context
            )
        current_plan_instruction = (
            self.get_current_plan_instruction()
        )
        if current_plan_instruction:
            parts.append(
                current_plan_instruction
            )
        return "\n".join(parts)

    def _execute_tool_with_telemetry(self, name, arguments):
        tool_started = time.perf_counter()
        try:
            tool_result = execute_tool_call(
                name,
                arguments,
            )
        except Exception:
            duration = time.perf_counter() - tool_started
            self.telemetry.record_tool_call(
                name,
                duration,
                False,
            )
            raise
        duration = time.perf_counter() - tool_started
        success = not (
            tool_result.startswith("Error:")
            or tool_result.startswith("Unknown tool:")
        )
        self.telemetry.record_tool_call(
            name,
            duration,
            success,
        )
        return tool_result