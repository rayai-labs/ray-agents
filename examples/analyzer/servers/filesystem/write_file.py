"""Write file tool wrapper for filesystem MCP server."""

from typing import Any

from ..mcp_client import call_mcp_tool


async def write_file(path: str, content: str) -> dict[str, Any]:
    """Write content to a file, creating it if it doesn't exist.

    Args:
        path: Path to the file to write
        content: Content to write to the file

    Returns:
        Dictionary containing:
        - success: True if successful
        - message: Success message
        - error: Error message (if failed)

    Example:
        >>> result = await write_file("output.txt", "Hello, world!")
        >>> if result.get("success"):
        ...     print(result["message"])
    """
    return await call_mcp_tool(
        "filesystem", "write_file", {"path": path, "content": content}
    )
