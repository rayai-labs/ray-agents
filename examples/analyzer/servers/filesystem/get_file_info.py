"""Get file info tool wrapper for filesystem MCP server."""

from typing import Any

from ..mcp_client import call_mcp_tool


async def get_file_info(path: str) -> dict[str, Any]:
    """Get metadata information about a file or directory.

    Args:
        path: Path to get info about

    Returns:
        Dictionary containing:
        - path: Full path
        - name: File/directory name
        - type: 'file' or 'directory'
        - size: Size in bytes
        - created: Creation timestamp
        - modified: Modification timestamp
        - accessed: Last access timestamp
        - error: Error message (if failed)

    Example:
        >>> result = await get_file_info("data.csv")
        >>> if "size" in result:
        ...     print(f"File size: {result['size']} bytes")
        ...     print(f"Last modified: {result['modified']}")
    """
    return await call_mcp_tool("filesystem", "get_file_info", {"path": path})
