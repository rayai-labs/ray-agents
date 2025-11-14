"""Execute code tool wrapper."""

import sys
from pathlib import Path
from typing import Any

import ray

# Import Ray code interpreter from main package
# This file is in: examples/analyzer/servers/code_executor/
# We need to import from: src/ray_agents/
project_root = Path(__file__).parent.parent.parent.parent.parent
src_path = project_root / "src"
if src_path.exists() and str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from ray_agents.code_interpreter import execute_code as ray_execute_code  # noqa: E402


async def execute_code(
    code: str,
    session_id: str = "default",
    image: str | None = None,
    dockerfile: str | None = None,
    timeout: int = 300,
) -> dict[str, Any]:
    """Execute Python code in a sandboxed environment with persistent variables.

    Args:
        code: Python code to execute
        session_id: Session identifier for persistent variables (default: "default")
        image: Optional Docker image name to use
        dockerfile: Optional Dockerfile content to build image
        timeout: Execution timeout in seconds (default: 300)

    Returns:
        Dictionary containing:
        - status: "success" or "error"
        - stdout: Standard output (if successful)
        - stderr: Standard error (if failed)
        - exit_code: Process exit code

    Example:
        >>> result = await execute_code("print('Hello world')")
        >>> print(result['stdout'])
        Hello world
    """
    from servers.code_executor.context import get_execution_context

    context = get_execution_context()

    kwargs = {
        "code": code,
        "session_id": session_id,
        "timeout": timeout,
    }

    if image:
        kwargs["image"] = image
    elif context.get("image"):
        kwargs["image"] = context["image"]

    if dockerfile:
        kwargs["dockerfile"] = dockerfile
    elif context.get("dockerfile"):
        kwargs["dockerfile"] = context["dockerfile"]

    if context.get("volumes"):
        kwargs["volumes"] = context["volumes"]

    result = ray.get(ray_execute_code.remote(**kwargs))

    return result
