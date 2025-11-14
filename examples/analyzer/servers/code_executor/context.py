"""Context for code execution.

This module maintains global context for code execution (volumes, image, etc.)
that the agent sets up during initialization.
"""

from typing import Any

_execution_context: dict[str, Any] = {}


def set_execution_context(
    volumes: dict[str, Any] | None = None,
    image: str | None = None,
    dockerfile: str | None = None,
) -> None:
    """Set the execution context for code_executor tools.

    Args:
        volumes: Docker volume mounts
        image: Docker image name
        dockerfile: Dockerfile content
    """
    global _execution_context
    _execution_context = {
        "volumes": volumes,
        "image": image,
        "dockerfile": dockerfile,
    }


def get_execution_context() -> dict[str, Any]:
    """Get the current execution context.

    Returns:
        Dictionary with volumes, image, and dockerfile
    """
    return _execution_context.copy()
