# Terminal-Native Coding Agent

A lightweight, terminal-native AI coding agent built from scratch.

The agent can understand coding tasks, create plans, inspect repositories, modify files, execute commands, interact with Git, recover from errors, and evaluate its own performance through a deterministic local benchmark.

The project deliberately avoids unnecessary framework complexity. The focus is on understanding and implementing the core systems behind a practical coding agent:

**LLM → Planning → Tool Calling → Execution → Validation → Evaluation**

---

## Overview

Most coding agents can be described as a loop around an LLM:

```text
                         ┌──────────────────────┐
                         │        User          │
                         │                      │
                         │  "Fix this bug..."   │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │        Agent         │
                         │                      │
                         │  Understand task     │
                         │  Build plan          │
                         │  Select tools        │
                         │  Interpret results   │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │        Model         │
                         │                      │
                         │  Reason + decide     │
                         │  next action         │
                         └──────────┬───────────┘
                                    │
                                    ▼
                    ┌─────────────────────────────────┐
                    │              Tools              │
                    │                                 │
                    │  read  write  search  execute   │
                    │  git   status  diff    commit   │ 
                    └────────────────┬────────────────┘
                                     │
                                     ▼
                         ┌──────────────────────┐
                         │      Workspace       │
                         │                      │
                         │   Files / Code / Git │
                         └──────────┬───────────┘
                                    │
                                    │ results
                                    ▼
                         ┌──────────────────────┐
                         │        Agent         │
                         │                      │
                         │  Observe result      │
                         │  Continue / revise   │
                         └──────────┬───────────┘
                                    │
                                    │
                                    ▼
                              Next iteration
```

The result is a small but complete coding-agent architecture rather than a collection of disconnected LLM calls.

---

# What It Can Do

The agent supports the core workflow expected from a terminal coding assistant.

```text
┌──────────────────────────────────────────────────────────────┐
│                     CODING AGENT                             │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Understand       Plan          Inspect         Modify       │
│      │              │              │               │         │
│      ▼              ▼              ▼               ▼         │
│   Task        Structured Plan   Repository      Files        │
│                                                              │
│                                                              │
│  Execute         Validate       Recover         Observe      │
│      │              │              │               │         │
│      ▼              ▼              ▼               ▼         │
│  Commands        Tests         Errors          Telemetry     │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Core capabilities

* Interactive terminal interface
* Multi-turn agent loop
* Structured planning
* LLM tool calling
* Repository inspection
* File creation and modification
* Code search
* Shell command execution
* Runtime error diagnosis
* Git operations
* Model fallback
* Workspace safety controls
* Structured run telemetry
* Automated evaluation
* Repository-context experiments

---

# Architecture

The system is intentionally divided into small, understandable components.

```text
                              ┌──────────────────┐
                              │     Terminal     │
                              │       CLI        │
                              └────────┬─────────┘
                                       │
                                       ▼
                              ┌──────────────────┐
                              │      Agent       │
                              │                  │
                              │  Conversation    │
                              │  Planning        │
                              │  Agent Loop      │
                              │  Tool Calling    │
                              └───────┬──────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    ▼                 ▼                 ▼
           ┌────────────────┐ ┌────────────────┐ ┌────────────────┐
           │  Model Router  │ │ Repository     │ │ Safety Layer   │
           │                │ │ Context        │ │                │
           │ Primary Model  │ │                │ │ Path checks    │
           │       ↓        │ │ File discovery │ │ Command checks │
           │ Fallback       │ │ Code search    │ │ Timeouts       │
           │       ↓        │ │ Relevant files │ │ Destructive    │
           │ Additional     │ │ Context input  │ │ operation      │
           │ Fallbacks      │ │                │ │ rejection      │
           └────────────────┘ └────────────────┘ └───────┬────────┘
                                                          │
                                                          ▼
                                                ┌──────────────────┐
                                                │      Tools       │
                                                │                  │
                                                │ read_file        │
                                                │ write_file       │
                                                │ list_files       │
                                                │ search_files     │
                                                │ run_command      │
                                                │ git_status       │
                                                │ git_diff         │
                                                │ git_add          │
                                                │ git_commit       │
                                                └────────┬─────────┘
                                                         │
                                                         ▼
                                                ┌──────────────────┐
                                                │    Workspace     │
                                                │                  │
                                                │  Source Code     │
                                                │  Tests           │
                                                │  Git Repository  │
                                                └──────────────────┘
```

The separation keeps the system easy to reason about and makes individual components independently testable.

---

# Agent Loop

At the center of the project is the agent loop.

```text
             ┌─────────────────────┐
             │      User Task      │
             └──────────┬──────────┘
                        │
                        ▼
             ┌─────────────────────┐
             │   Understand Task   │
             └──────────┬──────────┘
                        │
                        ▼
             ┌─────────────────────┐
             │   Create / Update   │
             │       Plan          │
             └──────────┬──────────┘
                        │
                        ▼
             ┌─────────────────────┐
             │     Call Model      │
             └──────────┬──────────┘
                        │
                        ▼
                 ┌───────────────┐
                 │ Tool required?│
                 └───────┬───────┘
                  Yes │      │ No
                      │      │
                      ▼      ▼
              ┌───────────┐ ┌──────────────┐
              │ Execute   │ │ Return final │
              │ Tool      │ │ response     │
              └─────┬─────┘ └──────────────┘
                    │
                    ▼
              ┌───────────┐
              │  Observe  │
              │  Result   │
              └─────┬─────┘
                    │
                    │
                    ▼
             Next iteration
```

This loop allows the model to operate on the repository incrementally rather than attempting to solve the entire task in one response.

---

# Tooling

The agent exposes a deliberately small tool surface.

| Tool           | Purpose                                   |
| -------------- | ----------------------------------------- |
| `read_file`    | Read source files                         |
| `write_file`   | Create or modify files                    |
| `list_files`   | Explore repository structure              |
| `search_files` | Search for relevant code                  |
| `run_command`  | Execute validated commands                |
| `git_status`   | Inspect repository state                  |
| `git_diff`     | Inspect modifications                     |
| `git_add`      | Stage changes                             |
| `git_commit`   | Create commits with explicit confirmation |

The goal is not to expose every possible system operation.

The goal is to provide enough capability for the model to perform meaningful coding tasks while keeping the execution surface controlled.

---

# Model Routing

Model availability is inherently unreliable in real-world agent systems.

The project therefore supports a fallback chain:

```text
                 ┌─────────────────┐
                 │   Primary Model │
                 └────────┬────────┘
                          │
                     unavailable?
                          │
                          ▼
                 ┌─────────────────┐
                 │  Fallback Model │
                 └────────┬────────┘
                          │
                     unavailable?
                          │
                          ▼
                 ┌─────────────────┐
                 │ Additional      │
                 │ Fallback Models │
                 └─────────────────┘
```

This allows the agent to continue operating when a preferred model is unavailable, rate-limited, or otherwise fails.

---

# Repository-Aware Context

A coding agent becomes substantially more useful when it understands the repository it is operating inside.

The project therefore includes repository-aware context mechanisms for:

* Discovering relevant files
* Searching source code
* Locating implementations
* Identifying important functions
* Supplying relevant repository information to the model

The context system was also evaluated experimentally rather than being treated as an assumed improvement.

---

# Repository Context Experiment

The same repository tasks were evaluated with and without repository-aware context.

```text
                 SAME TASKS
                     │
          ┌──────────┴──────────┐
          │                     │
          ▼                     ▼
    Context OFF             Context ON
          │                     │
          ▼                     ▼
    Agent searches       Relevant context
    repository itself    supplied earlier
          │                     │
          ▼                     ▼
       Results               Results
```

### Results

| Metric             | Context OFF | Context ON |
| ------------------ | ----------: | ---------: |
| Pass Rate          |       66.7% | **100.0%** |
| Average Turns      |        11.0 |    **6.7** |
| Average Tool Calls |         7.7 |    **4.7** |
| Average Duration   |       95.0s |     234.1s |

The most important result was the improvement in task success:

```text
66.7%  ───────────────────────────────►  100.0%
```

Average reasoning turns also decreased:

```text
11.0 turns  ──────────────────────────►  6.7 turns
```

And tool usage decreased:

```text
7.7 calls  ────────────────────────────►  4.7 calls
```

The experiment also exposed an important engineering tradeoff.

Context improved task reliability and reduced agent actions, but increased measured latency in this particular benchmark.

This makes the result more useful than simply claiming that "more context is better."

The practical lesson is:

> Better repository context can make an agent more reliable and efficient in its reasoning, but context acquisition and processing can introduce latency.

---

# Safety

Giving an LLM access to a shell and filesystem requires explicit boundaries.

The project therefore treats tool execution as a security boundary.

```text
                         Model
                           │
                           ▼
                  ┌─────────────────┐
                  │   Tool Request  │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ Safety Checks   │
                  │                 │
                  │ Path validation │
                  │ Command checks  │
                  │ Argument checks │
                  │ Timeout checks  │
                  │ Git validation  │
                  └────────┬────────┘
                           │
                    ┌──────┴──────┐
                    │             │
                 Allowed        Rejected
                    │             │
                    ▼             ▼
               Execute        Return error
                    │
                    ▼
                 Result
```

Current protections include:

* Workspace boundary enforcement
* Path validation
* Restricted command execution
* `shell=False`
* Command timeouts
* Destructive-command rejection
* Tool argument validation
* Git path validation
* Explicit confirmation before commits
* No automatic commits

The safety layer is intentionally separate from the agent itself so that model behavior does not directly determine what the host system is allowed to execute.

---

# Observability

Every agent run produces structured telemetry.

Example fields include:

```text
run_id
started_at
finished_at
model
turns
tool_calls
status
duration_seconds
model_calls
tools
error_type
error_message
```

Where available, token usage is also recorded.

A run can therefore be inspected as data rather than relying entirely on terminal output.

```text
                    Agent Run
                       │
                       ▼
              ┌─────────────────┐
              │   Execution     │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │   Telemetry     │
              │                 │
              │  turns          │
              │  tools          │
              │  duration       │
              │  model          │
              │  status         │
              │  errors         │
              └────────┬────────┘
                       │
                       ▼
                  runs.jsonl
```

This makes performance regressions and behavioral changes measurable.

---

# Evaluation

A coding agent should not be evaluated solely by whether its output "looks good."

This project includes a local benchmark designed around deterministic success conditions.

The evaluation runs tasks inside controlled workspaces and verifies whether the expected state was actually produced.

```text
                    Evaluation Task
                           │
                           ▼
                  ┌─────────────────┐
                  │ Controlled      │
                  │ Workspace       │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │      Agent      │
                  │                 │
                  │ Plan            │
                  │ Inspect         │
                  │ Modify          │
                  │ Execute         │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ Deterministic   │
                  │ Success Check   │
                  └────────┬────────┘
                           │
                     ┌─────┴─────┐
                     │           │
                   PASS         FAIL
                     │           │
                     ▼           ▼
                  Results      Results
```

---

# Benchmark Results

The current benchmark contains 13 tasks.

```text
                    EVALUATION

                 ┌──────────────┐
                 │   13 Tasks   │
                 └──────┬───────┘
                        │
                        ▼
              ┌──────────────────┐
              │    13 Passed     │
              └────────┬─────────┘
                       │
                       ▼
                  100% PASS
```

Current result:

```text
Tasks:             13
Passed:            13
Pass Rate:         100.0%
Average Turns:     4.6
Average Tool Calls: 1.9
Average Duration:  39.1s
```

The benchmark covers tasks including:

* Creating files
* Reading existing files
* Modifying functions
* Fixing runtime errors
* Searching repositories
* Locating implementations
* Diagnosing failures
* Multi-step modifications
* Inspecting Git state
* Testing command safety
* Validating agent behavior

---

# Testing

The project currently has:

```text
143 passed
```

Run the complete test suite with:

```text
python -m pytest -q
```

The test suite covers the core agent, tools, safety behavior, model routing, and evaluation-related functionality.

---

# Reviewer / Revision Architecture

The current implementation intentionally avoids turning the project into a large multi-agent framework.

A natural next extension is a lightweight reviewer/revision loop.

```text
                       ┌──────────────┐
                       │     User     │
                       └──────┬───────┘
                              │
                              ▼
                       ┌──────────────┐
                       │ Coding Agent │
                       │              │
                       │ Plan         │
                       │ Implement    │
                       └──────┬───────┘
                              │
                              ▼
                       ┌──────────────┐
                       │   Validate   │
                       │              │
                       │ Tests        │
                       │ Commands     │
                       │ Diff         │
                       └──────┬───────┘
                              │
                       ┌──────┴──────┐
                       │             │
                    Success       Failure
                       │             │
                       ▼             ▼
                   ┌───────┐   ┌────────────┐
                   │ Done  │   │  Reviewer  │
                   └───────┘   └─────┬──────┘
                                     │
                                     ▼
                              ┌────────────┐
                              │ Feedback   │
                              └─────┬──────┘
                                    │
                                    ▼
                              ┌────────────┐
                              │  Revision  │
                              └─────┬──────┘
                                    │
                                    │
                                    ▼
                                 Validate
```

The reviewer does not need to become an independent autonomous agent.
A simple implementation can:

1. Inspect the generated diff
2. Inspect test or command failures
3. Identify likely problems
4. Produce focused feedback
5. Allow the main agent to revise
6. Re-run validation

Conceptually:

```text
Generation
    ↓
Execution
    ↓
Validation
    ↓
Review
    ↓
Revision
    ↓
Validation
```

This preserves the simplicity of the existing architecture while introducing an important reliability pattern:

**Generation → Verification → Review → Revision**

The reviewer/revision system is therefore best treated as an extension to the current architecture rather than a requirement for the core implementation.

---

# Project Structure

```text
terminal-agent/
│
├── .env
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
│
├── logs/
│   └── runs.jsonl
│
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── agent.py
│   ├── model_router.py
│   └── tools.py
│
├── eval/
│   ├── tasks.json
│   ├── run.py
│   ├── run_repo_context_comparison.py
│   └── results.jsonl
│
└── tests/
    └── ...
```

The exact contents may evolve as the project grows, but the structure keeps runtime code, evaluation logic, telemetry, and tests clearly separated.

---

# Running the Project

## 1. Clone the repository

```text
git clone <your-repository-url>
cd terminal-agent
```

## 2. Create a virtual environment

Windows:

```text
python -m venv .venv
.venv\Scripts\activate
```

Linux / macOS:

```text
python3 -m venv .venv
source .venv/bin/activate
```

## 3. Install dependencies

```text
pip install -r requirements.txt
```

## 4. Configure environment variables

Create a `.env` file using `.env.example` as a reference.

Add the required model/API credentials.

## 5. Start the agent

```text
python -m src
```

Example:

```text
Terminal Agent

You > Find where the model fallback logic is implemented.

Agent > I found the fallback implementation in ...
```

---

# Running the Evaluation

Run the benchmark with:

```text
python -m eval.run
```

Run the repository-context comparison with:

```text
python -m eval.run_repo_context_comparison
```

Run tests with:

```text
python -m pytest -q
```

---

# Design Philosophy

The project intentionally favors simplicity over abstraction for its own sake.

The goal is not to recreate a production-scale coding platform.

The goal is to understand the systems that make coding agents work.

```text
                         ┌──────────────────┐
                         │       LLM        │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │  Tool Calling    │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │    Agent Loop    │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │     Planning     │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │ Read / Write /   │
                         │ Execute / Git    │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │      Safety      │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │  Observability   │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │    Evaluation    │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │ Repository       │
                         │ Context          │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │ Review /         │
                         │ Revision         │
                         └──────────────────┘
```

Each layer exists because it solves a concrete problem.

The architecture is intentionally small enough that the entire system can be understood without introducing a heavyweight orchestration framework.

---

# Engineering Tradeoffs

The project intentionally exposes several real engineering tradeoffs.

### Reliability vs. latency

Repository context improved benchmark success from **66.7% to 100%**, but increased measured latency in the experiment.

### Autonomy vs. safety

More powerful tools allow the model to accomplish more, but increase the consequences of incorrect decisions.

The safety layer therefore restricts what the model can execute.

### Simplicity vs. sophistication

A multi-agent architecture could introduce additional reviewers, planners, critics, and specialized workers.

However, additional agents also introduce additional coordination, latency, and failure modes.

The current architecture therefore favors a single capable agent with a lightweight review/revision extension.

### Automation vs. control

Git operations are available, but commits require explicit confirmation.

The system assists with repository management without silently taking irreversible actions.

---

# Key Results

```text
┌────────────────────────────────────────────────────────────┐
│                       PROJECT RESULTS                      │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Automated Tests                 143 passed                │
│                                                            │
│  Evaluation                      13 / 13 passed            │
│                                   100% success             │
│                                                            │
│  Repository Context              66.7% → 100%              │
│  Pass Rate                                                 │
│                                                            │
│  Average Turns                   11.0 → 6.7                │
│                                                            │
│  Average Tool Calls              7.7 → 4.7                 │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

These results provide measurable evidence that the implemented architecture is functional rather than merely demonstrating an LLM calling tools.

---

# Future Work

Potential extensions include:

* Lightweight reviewer/revision loop
* Improved repository retrieval
* Context ranking
* Better context caching
* Latency optimization
* More diverse benchmark tasks
* Regression testing across model configurations
* Patch-based code review
* Improved failure recovery
* More detailed evaluation metrics

These are extensions to the current system rather than prerequisites for the core project.

---

# Final Status

```text
LLM Integration                 ✓
Model Routing / Fallback        ✓
Tool Calling                    ✓
Agent Loop                      ✓
Structured Planning             ✓
File Operations                 ✓
Command Execution               ✓
Git Operations                  ✓
Safety Controls                 ✓
Observability                   ✓
Automated Tests                 ✓
Evaluation Harness              ✓
Repository Context              ✓
Context Comparison              ✓
Reviewer / Revision Design      ✓
```

```text
                    ┌────────────────────────┐
                    │                        │
                    │       COMPLETED        │
                    │                        │
                    └────────────────────────┘
```

---

# What This Project Demonstrates

This project demonstrates practical understanding of:

**AI agents**

Designing an iterative agent that reasons, selects tools, observes results, and continues execution.

**LLM tool calling**

Connecting model decisions to controlled filesystem, shell, and Git operations.

**Agent reliability**

Using planning, fallback models, repository context, validation, and error recovery to improve task completion.

**AI safety**

Treating model-generated actions as untrusted input and validating them before execution.

**Observability**

Recording structured execution telemetry for debugging and analysis.

**Evaluation**

Measuring agent behavior through deterministic tasks rather than relying only on subjective inspection.

**Repository-aware reasoning**

Testing whether providing relevant codebase context actually improves agent performance.

**Engineering tradeoffs**

Measuring reliability, tool usage, reasoning steps, and latency rather than optimizing a single metric blindly.

**Agentic software architecture**

Keeping the core system simple while leaving a clear path toward reviewer/revision workflows.

---

## Summary

The project started with a simple idea:

```text
"Give an LLM tools and let it modify a repository."
```

It evolved into a complete coding-agent system:

```text
                   ┌────────────────────┐
                   │       User         │
                   └─────────┬──────────┘
                             │
                             ▼
                   ┌────────────────────┐
                   │      Agent         │
                   └─────────┬──────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
          Planning         Context        Routing
              │              │              │
              └──────────────┼──────────────┘
                             │
                             ▼
                         Tool Use
                             │
                             ▼
                      Safety Checks
                             │
                             ▼
                        Workspace
                             │
                             ▼
                         Validation
                             │
                             ▼
                        Telemetry
                             │
                             ▼
                         Evaluation
                             │
                             ▼
                     Review / Revision
```

The result is a compact, measurable, and extensible terminal-native coding agent built around the fundamental systems that make modern AI coding tools useful.
