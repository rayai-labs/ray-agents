"""List directory tool wrapper for filesystem MCP server."""

from typing import Any

from ..mcp_client import call_mcp_tool


async def list_directory(path: str) -> dict[str, Any]:
    """List contents of a directory.

    Args:
        path: Path to the directory to list

    Returns:
        Dictionary containing:
        - entries: List of directory entries, each with:
            - name: Entry name
            - type: 'file' or 'directory'
            - path: Full path
            - size: File size in bytes (for files only)
        - error: Error message (if failed)

    Example:
        >>> result = await list_directory("./data")
        >>> if "entries" in result:
        ...     for entry in result["entries"]:
        ...         print(f"{entry['name']} ({entry['type']})")
    """
    return await call_mcp_tool("filesystem", "list_directory", {"path": path})
