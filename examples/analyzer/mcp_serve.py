"""Ray Serve deployment for MCP Filesystem Server.

This runs the MCP filesystem server as a Ray Serve deployment,
providing HTTP access to filesystem operations.
"""

from pathlib import Path
from typing import Any

import ray
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from ray import serve

app = FastAPI()


class FilesystemMCPServer:
    """MCP Filesystem server that operates on the host filesystem."""

    def __init__(self, allowed_directories: list[str]):
        """Initialize with allowed directories.

        Args:
            allowed_directories: List of directories that can be accessed
        """
        self.allowed_directories = [Path(d).resolve() for d in allowed_directories]

    def _is_path_allowed(self, path: Path) -> bool:
        """Check if a path is within allowed directories."""
        resolved_path = path.resolve()
        return any(
            str(resolved_path).startswith(str(allowed_dir))
            for allowed_dir in self.allowed_directories
        )

    def read_file(self, path: str) -> dict[str, Any]:
        """Read file contents."""
        file_path = Path(path)

        if not self._is_path_allowed(file_path):
            return {"error": f"Access denied: {path} is outside allowed directories"}

        if not file_path.exists():
            return {"error": f"File not found: {path}"}

        if not file_path.is_file():
            return {"error": f"Not a file: {path}"}

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
            return {"content": content}
        except Exception as e:
            return {"error": f"Error reading file: {str(e)}"}

    def write_file(self, path: str, content: str) -> dict[str, Any]:
        """Write content to a file."""
        file_path = Path(path)

        if not self._is_path_allowed(file_path):
            return {"error": f"Access denied: {path} is outside allowed directories"}

        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return {"success": True, "message": f"Successfully wrote to {path}"}
        except Exception as e:
            return {"error": f"Error writing file: {str(e)}"}

    def list_directory(self, path: str) -> dict[str, Any]:
        """List directory contents."""
        dir_path = Path(path)

        if not self._is_path_allowed(dir_path):
            return {"error": f"Access denied: {path} is outside allowed directories"}

        if not dir_path.exists():
            return {"error": f"Directory not found: {path}"}

        if not dir_path.is_dir():
            return {"error": f"Not a directory: {path}"}

        try:
            entries = []
            for item in sorted(dir_path.iterdir()):
                entry = {
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "path": str(item),
                }
                if item.is_file():
                    entry["size"] = item.stat().st_size
                entries.append(entry)

            return {"entries": entries}
        except Exception as e:
            return {"error": f"Error listing directory: {str(e)}"}

    def search_files(self, path: str, pattern: str) -> dict[str, Any]:
        """Search for files matching a pattern."""
        search_path = Path(path)

        if not self._is_path_allowed(search_path):
            return {"error": f"Access denied: {path} is outside allowed directories"}

        if not search_path.exists():
            return {"error": f"Directory not found: {path}"}

        if not search_path.is_dir():
            return {"error": f"Not a directory: {path}"}

        try:
            matches = []
            for match in search_path.glob(pattern):
                if self._is_path_allowed(match):
                    matches.append(
                        {
                            "path": str(match),
                            "type": "directory" if match.is_dir() else "file",
                        }
                    )

            return {"matches": matches, "count": len(matches)}
        except Exception as e:
            return {"error": f"Error searching files: {str(e)}"}

    def get_file_info(self, path: str) -> dict[str, Any]:
        """Get file or directory information."""
        file_path = Path(path)

        if not self._is_path_allowed(file_path):
            return {"error": f"Access denied: {path} is outside allowed directories"}

        if not file_path.exists():
            return {"error": f"Path not found: {path}"}

        try:
            stat = file_path.stat()
            info = {
                "path": str(file_path),
                "name": file_path.name,
                "type": "directory" if file_path.is_dir() else "file",
                "size": stat.st_size,
                "created": stat.st_ctime,
                "modified": stat.st_mtime,
                "accessed": stat.st_atime,
            }
            return info
        except Exception as e:
            return {"error": f"Error getting file info: {str(e)}"}

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a tool with the given arguments."""
        tools = {
            "read_file": self.read_file,
            "write_file": self.write_file,
            "list_directory": self.list_directory,
            "search_files": self.search_files,
            "get_file_info": self.get_file_info,
        }

        if tool_name not in tools:
            return {"error": f"Unknown tool: {tool_name}"}

        handler = tools[tool_name]

        try:
            result = handler(**arguments)
            return result
        except TypeError as e:
            return {"error": f"Invalid arguments: {str(e)}"}
        except Exception as e:
            return {"error": f"Tool execution failed: {str(e)}"}


@serve.deployment(num_replicas=1)
@serve.ingress(app)
class MCPServeDeployment:
    """Ray Serve deployment for MCP filesystem server."""

    def __init__(self, allowed_directories: list[str]):
        """Initialize the MCP server deployment.

        Args:
            allowed_directories: List of directories that can be accessed
        """
        self.server = FilesystemMCPServer(allowed_directories)

    @app.post("/tools/call")
    async def call_tool(self, request: dict) -> JSONResponse:
        """Handle MCP tool calls via HTTP.

        Request format:
        {
            "tool": "read_file",
            "arguments": {"path": "/path/to/file"}
        }
        """
        try:
            tool_name = request.get("tool")
            arguments = request.get("arguments", {})

            if not tool_name:
                raise HTTPException(status_code=400, detail="Missing 'tool' field")

            result = self.server.call_tool(tool_name, arguments)
            return JSONResponse(content=result)

        except Exception as e:
            return JSONResponse(
                status_code=500, content={"error": f"Server error: {str(e)}"}
            )

    @app.get("/health")
    async def health(self):
        """Health check endpoint."""
        return {"status": "healthy"}


def start_mcp_server(allowed_directories: list[str], port: int = 8265) -> Any | None:
    """Start the MCP filesystem server as a Ray Serve deployment.

    Args:
        allowed_directories: List of directories that can be accessed
        port: Port for Ray Serve (default: 8265)

    Returns:
        Deployment handle or None if already running
    """
    if not ray.is_initialized():
        ray.init(ignore_reinit_error=True)

    try:
        from ray.serve._private.api import _get_global_client

        _get_global_client()

        try:
            existing_apps = serve.status().applications
            if "mcp-filesystem" in existing_apps:
                print(
                    f"✓ MCP Filesystem Server already running at http://localhost:{port}/mcp"
                )
                return None
        except Exception:
            pass

    except Exception:
        serve.start(detached=True, http_options={"host": "0.0.0.0", "port": port})

    deployment = MCPServeDeployment.bind(allowed_directories=allowed_directories)

    serve.run(
        deployment,
        name="mcp-filesystem",
        route_prefix="/mcp",
    )

    print(f"✓ MCP Filesystem Server running at http://localhost:{port}/mcp")
    print(f"  Allowed directories: {allowed_directories}")
    print(f"  Health check: http://localhost:{port}/mcp/health")

    return deployment


if __name__ == "__main__":
    examples_dir = Path(__file__).parent.parent
    allowed_dirs = [
        str(examples_dir / "datasets"),
        str(examples_dir / "servers"),
    ]

    print("Starting MCP Filesystem Server...")
    start_mcp_server(allowed_dirs)

    print("\nServer is running. Press Ctrl+C to stop.")
    try:
        import time

        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        serve.shutdown()
