"""Filesystem MCP server tool wrappers.

This module provides Python wrappers for the filesystem MCP server tools.
Each tool is available as an async function that can be called directly.

Available tools:
- read_file: Read file contents
- write_file: Write content to a file
- list_directory: List directory contents
- search_files: Search for files by pattern
- get_file_info: Get file metadata

Example:
    from servers.filesystem import read_file, list_directory

    result = await read_file("data.txt")
    if "content" in result:
        print(result["content"])

    result = await list_directory("./data")
    for entry in result.get("entries", []):
        print(entry["name"])
"""

from .get_file_info import get_file_info
from .list_directory import list_directory
from .read_file import read_file
from .search_files import search_files
from .write_file import write_file

__all__ = [
    "read_file",
    "write_file",
    "list_directory",
    "search_files",
    "get_file_info",
]
