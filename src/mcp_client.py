import asyncio
import queue
import threading
from pathlib import Path
import sys
import os

from mcp import Client, StdioServerParameters


class MCPToolClient:
    """
    Synchronous bridge around the asynchronous MCP v2 Client.

    A dedicated asyncio task owns the complete MCP client lifecycle.
    The synchronous Agent communicates with that task through queues.
    """

    def __init__(self, server_script, workspace=None):
        self.server_script = Path(server_script).resolve()
        if workspace is None:
            workspace = self.server_script.parent.parent
        self.workspace = Path(workspace).resolve()

        self._commands = queue.Queue()
        self._responses = queue.Queue()

        self._thread = threading.Thread(
            target=self._run_thread,
            daemon=True,
        )

        self._started = False
        self._stopped = False

    async def _mcp_loop(self):
        server_params = StdioServerParameters(
            command=sys.executable,
            args=[str(self.server_script)],
            cwd=str(self.workspace),
            env={
                **os.environ,
                "TERMINAL_AGENT_WORKSPACE": str(self.workspace),
            },
        )

        # IMPORTANT:
        # The entire MCP lifecycle lives inside this single async task.
        async with Client(server_params) as client:

            while True:
                command = await asyncio.to_thread(
                    self._commands.get
                )

                operation = command[0]

                if operation == "list_tools":
                    result = await client.list_tools()
                    self._responses.put(
                        ("ok", result.tools)
                    )

                elif operation == "call_tool":
                    _, name, arguments = command

                    result = await client.call_tool(
                        name,
                        arguments or {},
                    )

                    self._responses.put(
                        ("ok", result)
                    )

                elif operation == "close":
                    self._responses.put(
                        ("ok", None)
                    )
                    break

    def _run_thread(self):
        asyncio.run(self._mcp_loop())

    def _send(self, command):
        self._commands.put(command)

        status, value = self._responses.get()

        if status == "error":
            raise value

        return value

    def start(self):
        if self._started:
            return

        self._thread.start()
        self._started = True

    def list_tools(self):
        if not self._started:
            raise RuntimeError(
                "MCP client is not started."
            )

        return self._send(
            ("list_tools",)
        )

    def call_tool(self, name, arguments=None):
        if not self._started:
            raise RuntimeError(
                "MCP client is not started."
            )

        return self._send(
            (
                "call_tool",
                name,
                arguments or {},
            )
        )

    def close(self):
        if not self._started or self._stopped:
            return

        self._send(("close",))

        self._thread.join(timeout=10)

        self._stopped = True


def format_mcp_result(result):
    if result.is_error:
        text_parts = []

        for content in result.content:
            if getattr(content, "type", None) == "text":
                text_parts.append(content.text)

        if text_parts:
            return "MCP tool error: " + "\n".join(text_parts)

        return "MCP tool error."

    if result.structured_content:
        structured = result.structured_content

        if isinstance(structured, dict):
            value = structured.get("result")

            if value is not None:
                return str(value)

        return str(structured)

    text_parts = []

    for content in result.content:
        if getattr(content, "type", None) == "text":
            text_parts.append(content.text)

    return "\n".join(text_parts)


if __name__ == "__main__":
    server_script = (
        Path(__file__).resolve().parent /
        "mcp_server.py"
    )

    client = MCPToolClient(server_script)

    try:
        client.start()

        tools = client.list_tools()

        print("Available MCP tools:")

        for tool in tools:
            print(f"  - {tool.name}")

        result = client.call_tool(
            "search_repository",
            {
                "query": "validation",
                "limit": 5,
            },
        )

        print("\nMCP result:")
        print(format_mcp_result(result))

    finally:
        client.close()