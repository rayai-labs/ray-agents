"""Search files tool wrapper for filesystem MCP server."""

from typing import Any

from ..mcp_client import call_mcp_tool


async def search_files(path: str, pattern: str) -> dict[str, Any]:
    """Search for files matching a pattern.

    Args:
        path: Directory to search in
        pattern: Glob pattern to match (e.g., '*.py', '**/*.txt')

    Returns:
        Dictionary containing:
        - matches: List of matching files, each with:
            - path: Full path to the file
            - type: 'file' or 'directory'
        - count: Number of matches
        - error: Error message (if failed)

    Example:
        >>> result = await search_files("./src", "**/*.py")
        >>> if "matches" in result:
        ...     print(f"Found {result['count']} Python files")
        ...     for match in result["matches"]:
        ...         print(match["path"])
    """
    return await call_mcp_tool(
        "filesystem", "search_files", {"path": path, "pattern": pattern}
    )
