# Terminal Coding Agent v0.1

A lightweight terminal-based coding agent built in Python. It uses a Groq-hosted model, maintains a conversation loop, and can call tools to read files, write files, and run shell commands from inside the workspace.

## Features

- LLM integration
- tool calling
- agent loop
- file reading
- file modification
- shell execution
- iterative coding

## Project structure

- `src/main.py` — chat loop and orchestration
- `src/tools.py` — filesystem and shell tools exposed to the model
- `hello.py` — simple sample script
- `calculator.py` — small example script
- `.env.example` — example env configuration

## Setup

1. Copy `.env.example` to `.env`
2. Add your Groq API key:
   ```bash
   GROQ_API_KEY=your_key_here
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the agent:
   ```bash
   python src/main.py
   ```

## Notes

This repository is intended as a minimal but coherent agent project—enough to demonstrate an interview-ready coding agent workflow and a clean release milestone.

## Release

```bash
git tag v0.1
```
