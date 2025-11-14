"""Read file tool wrapper for filesystem MCP server."""

from typing import Any

from ..mcp_client import call_mcp_tool


async def read_file(path: str) -> dict[str, Any]:
    """Read the complete contents of a file from the file system.

    Args:
        path: Path to the file to read

    Returns:
        Dictionary containing:
        - content: The file contents (if successful)
        - error: Error message (if failed)

    Example:
        >>> result = await read_file("data/example.txt")
        >>> if "content" in result:
        ...     print(result["content"])
    """
    return await call_mcp_tool("filesystem", "read_file", {"path": path})
