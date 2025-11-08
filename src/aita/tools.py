# tools.py
from __future__ import annotations

from typing import Any

from langchain.tools import tool
from aita.command_safety import validate_command_safety
from aita.utils import DockerEnvironment


def make_execute_bash_tool(env: DockerEnvironment):
    """
    Create a LangChain tool that runs bash commands inside the given DockerEnvironment.
    """

    @tool("execute_bash")
    def execute_bash(command: str, timeout: int = 30) -> dict[str, Any]:
        """
        Execute a *simple* bash command (ls, cat, grep, find, etc.) inside the
        sandbox container and return stdout, returncode, and safety info.

        This tool is intended only for read-only exploration of the filesystem.
        """
        safety = validate_command_safety(command)
        if not safety.is_safe:
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": f"Command blocked by safety checks: {safety.reason}",
            }

        result = env.execute(command, timeout=timeout)
        return {
            "success": result["returncode"] == 0,
            "returncode": result["returncode"],
            "stdout": result["output"],
            "stderr": "" if result["returncode"] == 0 else "Non-zero exit code.",
        }

    # The decorator returns a Tool instance
    return execute_bash
