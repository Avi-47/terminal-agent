from pathlib import Path
import json
import time
from .validator import validate_workspace
from .mcp_client import MCPToolClient, format_mcp_result
from .model_router import MODELS, create_response
from . import tools
from .tools import (
    TOOLS,
    execute_tool_call,
    git_diff,
    git_status,
    set_workspace_root,
)
from .telemetry import RunTelemetry
from .reviewer import (
    REVIEW_INSTRUCTIONS,
    parse_review_response,
)
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
        workspace=None,
        max_iterations=10,
        enable_reviewer=True,
        use_repo_context=True,
        enable_validation=True,
        confirm_callback=None,
        enable_mcp=False,
    ):
        self.client = client
        if workspace is not None:
            set_workspace_root(workspace)
        self.confirm_callback = confirm_callback
        self.commit_confirmed = False
        self.conversation = []
        self.max_iterations = 10
        self.enable_validation = enable_validation
        self.max_validation_attempts = 3
        self.validation_attempts = 0
        self.stress_test_config = None
        self.enable_mcp = enable_mcp
        self.mcp_client = None
        self.mcp_tools = []
        self.mcp_tool_names = set()
        self.max_review_cycles = 1
        self.enable_reviewer = enable_reviewer
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

            "Only use tools whose exact names appear in the provided tool definitions."
            "Never invent, rename, namespace, or assume a tool such as"
            "repo_browser.print_tree or any other tool that is not explicitly provided."
            "If you need repository structure, use list_files."
            "If you need to find text, use search_files."
            "If you need file contents, use read_file."

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

            "When a task requires finding a Python symbol's definition and repository "
            "references, prefer the MCP symbol-analysis tool when it is available."
            "Use native repository tools for general file inspection, editing, command"
            "execution, and Git operations."

            "VALIDATION RESULT messages are objective execution evidence. "
            "A PASS means the configured validation checks completed successfully. "
            "A FAIL means the model should inspect the reported failure, make an "
            "appropriate correction, and allow validation to run again. "
            "Do not ignore successful validation and repeat equivalent checks "
            "without a reason. "
            
            "After modifying code, normally verify the change. "
            "Deterministic validation results provided by the system count as "
            "verification evidence when they successfully validate the relevant "
            "workspace. Do not perform redundant verification merely because a "
            "plan task contains the word 'verify'. If validation has already "
            "passed, use that evidence to determine whether the verification "
            "task is satisfied. "
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

    def validate_workspace(self):
        """
        Run deterministic validation checks against the current workspace.
        """
        result = validate_workspace(
            self.get_workspace_root(),
            stress_config=self.stress_test_config,
        )
        print("\nValidator >")
        print(result.to_text())
        return result

    def start_mcp(self):
        if not self.enable_mcp:
            return

        server_script = (
            Path(__file__).resolve().parent /
            "mcp_server.py"
        )

        self.mcp_client = MCPToolClient(
            server_script,
            workspace=self.get_workspace_root(),
        )

        self.mcp_client.start()

        tools = self.mcp_client.list_tools()

        self.mcp_tools = []
        self.mcp_tool_names = set()

        for tool in tools:
            tool_name = f"mcp_{tool.name}"

            self.mcp_tools.append(
                {
                    "type": "function",
                    "name": tool_name,
                    "description": (
                        tool.description
                        or f"MCP tool: {tool.name}"
                    ),
                    "parameters": tool.input_schema,
                }
            )

            self.mcp_tool_names.add(tool_name)


    def stop_mcp(self):
        if getattr(self, "mcp_client", None) is None:
            return

        try:
            self.mcp_client.close()
        finally:
            self.mcp_client = None
            self.mcp_tools = []
            self.mcp_tool_names = set()

    def get_model_tools(self):
        return TOOLS + self.mcp_tools

    def configure_stress_test(self, config):
        """
        Configure an optional oracle-based stress test.
        Expected configuration:
            {
                "candidate_path": "...",
                "reference_path": "...",
                "generator_path": "...",
                "trials": 20,
                "timeout": 5,
            }
        """
        if config is None:
            self.stress_test_config = None
            return
        if not isinstance(config, dict):
            raise ValueError(
                "stress test configuration must be a dictionary"
            )
        required = {
            "candidate_path",
            "reference_path",
            "generator_path",
        }
        missing = required - config.keys()
        if missing:
            raise ValueError(
                "stress test configuration is missing: "
                f"{sorted(missing)}"
            )
        self.stress_test_config = {
            "candidate_path": config["candidate_path"],
            "reference_path": config["reference_path"],
            "generator_path": config["generator_path"],
            "trials": config.get("trials", 20),
            "timeout": config.get("timeout", 5),
        }

    def should_validate_after_tools(self, tool_names):
        """
        Validation is useful after tools that can modify the workspace.
        """
        modifying_tools = {
            "write_file",
        }
        return any(
            name in modifying_tools
            for name in tool_names
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

    def capture_workspace_baseline(self):
        """
        Capture the Git state before an agent run.
        This allows the reviewer to distinguish changes made during
        the current agent run from changes that already existed.
        """
        return {
            "git_status": git_status(),
            "git_diff": git_diff(),
        }

    def build_review_context(self, prompt, agent_result, baseline,):
        """
        Build evidence for the independent reviewer.
        Existing workspace changes from before the agent run are
        separated from changes observed after the run.
        """
        current_status = git_status()
        current_diff = git_diff()
        baseline_diff = baseline.get(
            "git_diff",
            "",
        )
        if current_diff == baseline_diff:
            agent_changes = (
                "No unstaged Git diff changes were detected during "
                "this agent run."
            )
        else:
            agent_changes = current_diff
        return {
            "user_request": prompt,
            "agent_result": agent_result,
            "baseline_git_status": baseline.get(
                "git_status",
                "",
            ),
            "current_git_status": current_status,
            "agent_run_changes": agent_changes,
        }
    
    def review_result(self, prompt, agent_result, baseline,):
        """
        Ask an independent LLM call to review the completed agent work.
        """
        review_context = self.build_review_context(
            prompt,
            agent_result,
            baseline,
        )
        review_conversation = [
            {
                "role": "user",
                "content": json.dumps(
                    review_context,
                    indent=2,
                ),
            }
        ]
        model_started = time.perf_counter()
        try:
            response = create_response(
                self.client,
                MODELS,
                REVIEW_INSTRUCTIONS,
                review_conversation,
                [],
            )
        except Exception:
            model_duration = (
                time.perf_counter() - model_started
            )
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
        review = parse_review_response(
            response.output_text
        )
        print("\nReviewer >")
        print(
            f"Decision: {review['decision']}"
        )
        print(
            f"Reason: {review['reason']}"
        )
        return review

    def build_revision_prompt(self, original_prompt, review,):
        """
        Build a focused follow-up request after reviewer rejection.
        """
        return (
            "The previous attempt has been independently reviewed and "
            "requires correction.\n\n"
            "ORIGINAL USER REQUEST:\n"
            f"{original_prompt}\n\n"
            "REVIEWER FEEDBACK:\n"
            f"{review['reason']}\n\n"
            "REQUIRED REVISION:\n"
            f"{review['revision_instructions']}\n\n"
            "Inspect the current workspace state. Correct only the issues "
            "identified by the reviewer where appropriate. Verify the "
            "result before finishing."
        )

    def run(self, prompt, stress_config=None):
        self.configure_stress_test(stress_config)
        self.telemetry = RunTelemetry(
            model=self.get_model_name(),
        )
        self.validation_attempts = 0

        self.start_mcp()

        try:
            baseline = self.capture_workspace_baseline()
            result = self._run(prompt)

            if not self.enable_reviewer:
                self.telemetry.finish(
                    status="success"
                )
                print(self.telemetry.summary())
                return result

            review = self.review_result(
                prompt,
                result,
                baseline,
            )

            if review["decision"] == "APPROVE":
                self.telemetry.finish(
                    status="success"
                )
                print(self.telemetry.summary())
                return result

            print("\nReviewer rejected the result.")
            print("Starting one revision attempt...")

            revision_prompt = self.build_revision_prompt(
                prompt,
                review,
            )

            self.conversation = []
            self.plan = []
            self.current_plan_index = 0
            self.validation_attempts = 0

            revision_baseline = (
                self.capture_workspace_baseline()
            )

            revised_result = self._run(
                revision_prompt
            )

            final_review = self.review_result(
                prompt,
                revised_result,
                revision_baseline,
            )

            if final_review["decision"] == "APPROVE":
                self.telemetry.finish(
                    status="success"
                )
            else:
                self.telemetry.finish(
                    status="review_rejected",
                    error=RuntimeError(
                        final_review["reason"]
                    ),
                )

            print(self.telemetry.summary())
            return revised_result

        except Exception as error:
            self.telemetry.finish(
                status="error",
                error=error,
            )
            print(self.telemetry.summary())
            raise

        finally:
            self.stop_mcp()

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
                self.get_model_tools(),
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
            executed_tool_names = []
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
                executed_tool_names.append(item.name)
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
            # If there were no tool calls, the model has not performed
            # any concrete workspace action yet.
            if not tool_outputs:
                # If a plan task is currently in progress, do NOT mark it
                # complete merely because the model returned text.
                if (
                    self.plan
                    and self.current_plan_index < len(self.plan)
                    and self.plan[self.current_plan_index]["status"]
                    == "in_progress"
                ):
                    self.conversation.append({
                        "role": "user",
                        "content": (
                            "The current plan task has not been completed yet. "
                            "You did not execute any tool call. "
                            "Complete the current plan task using the available tools. "
                            "Do not claim completion without performing the required action."
                        ),
                    })
                    model_started = time.perf_counter()
                    try:
                        response = create_response(
                            self.client,
                            MODELS,
                            self.get_model_instructions(),
                            self.conversation,
                            self.get_model_tools(),
                        )
                    except Exception:
                        model_duration = (
                            time.perf_counter() - model_started
                        )
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
                # No plan is active. A response without tool calls is a
                # legitimate final response.
                return response.output_text
            
            # Save tool results.
            self.conversation.extend(tool_outputs)
            # Run deterministic validation after workspace modifications.
            if (self.enable_validation 
                and self.should_validate_after_tools(executed_tool_names)
                and self.validation_attempts < self.max_validation_attempts
            ):
                self.validation_attempts += 1
                validation_result = self.validate_workspace()
                validation_text = validation_result.to_text()
                self.conversation.append({
                    "role": "user",
                    "content": (
                        "\n"
                        + validation_text
                        + "\n\n"
                        "Use this validation evidence to determine the next action. "
                        "If validation failed, inspect the failure, correct the relevant "
                        "code, and run the appropriate verification again. "
                        "If validation passed and the user's request is satisfied, "
                        "do not make unnecessary changes."
                    ),
                })
                if not validation_result.passed:
                    print(
                        "\nValidator found failures. "
                        "Returning evidence to the agent."
                    )
                if (self.validation_attempts >= self.max_validation_attempts and not validation_result.passed):
                    print("\nValidator stopped after maximum validation attempts.")

            model_started = time.perf_counter()
            try:
                response = create_response(
                    self.client,
                    MODELS,
                    self.get_model_instructions(),
                    self.conversation,
                    self.get_model_tools(),
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
            if name in self.mcp_tool_names:
                if isinstance(arguments, str):
                    arguments = json.loads(arguments)
                actual_name = name[len("mcp_"):]
                result = self.mcp_client.call_tool(
                    actual_name,
                    arguments,
                )
                tool_result = format_mcp_result(result)
            else:
                tool_result = execute_tool_call(name, arguments)
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