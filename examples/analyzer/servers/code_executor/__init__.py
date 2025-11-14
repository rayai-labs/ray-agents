"""Code executor MCP server tool wrappers.

This module provides a Python wrapper for executing code in a sandboxed environment.

Available tools:
- execute_code: Execute Python code with persistent variables

Example:
    from servers.code_executor import execute_code

    result = await execute_code("print('Hello world')")
    if "stdout" in result:
        print(result["stdout"])
"""

from .execute_code import execute_code

__all__ = ["execute_code"]
