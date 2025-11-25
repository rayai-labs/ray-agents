"""Serve projects locally with Ray Serve."""

import importlib.util
import inspect
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import click

from ray_agents.decorators import get_agent_resources, has_resource_config


@click.command(
    context_settings={"allow_extra_args": True, "allow_interspersed_args": False}
)
@click.argument("project_path", default=".")
@click.option("--port", default=8000, help="Port to serve on")
@click.option("--agents", help="Deploy specific agents (comma-separated)")
@click.pass_context
def serve(ctx, project_path: str, port: int, agents: str):
    """Serve agents using Ray Serve."""
    project_dir = Path(project_path).resolve()

    if not project_dir.exists():
        click.echo(f"Error: Project directory not found: {project_dir}")
        return

    cli_resources = _parse_resource_flags(ctx.args)

    if not _ensure_dependencies():
        return

    agents_dict = _discover_agents(project_dir)
    if not agents_dict:
        click.echo("Error: No agents found")
        click.echo("Create agents/ directory with Agent classes")
        return

    agents_to_deploy = _select_agents(agents_dict, agents)
    if not agents_to_deploy:
        return

    _deploy_agents(agents_to_deploy, port, cli_resources)


def _parse_resource_flags(extra_args: list[str]) -> dict[str, dict[str, Any]]:
    """
    Parse CLI resource flags with format --{agent-name}-{resource-type}={value}.

    Args:
        extra_args: List of extra CLI arguments

    Returns:
        Dict mapping agent names to their resource configurations
    """
    cli_resources: dict[str, dict[str, Any]] = {}
    resource_types = ["num-cpus", "memory", "num-replicas", "num-gpus"]

    for arg in extra_args:
        if not arg.startswith("--"):
            continue

        if "=" not in arg:
            click.echo(
                f"Warning: Ignoring invalid resource flag '{arg}' (missing =value)"
            )
            continue

        flag_name, value = arg[2:].split("=", 1)

        if "-" not in flag_name:
            continue

        parts = flag_name.split("-")
        if len(parts) < 2:
            continue

        resource_type: str | None = None
        agent_name: str | None = None

        for rt in resource_types:
            if flag_name.endswith(f"-{rt}"):
                resource_type = rt
                agent_name = flag_name[: -len(f"-{rt}")]
                break

        if resource_type is None or agent_name is None:
            continue

        try:
            parsed_value: int | str
            if resource_type in ["num-cpus", "num-replicas", "num-gpus"]:
                parsed_value = int(value)
            else:
                parsed_value = value

            decorator_param = resource_type.replace("-", "_")

            if agent_name not in cli_resources:
                cli_resources[agent_name] = {}
            cli_resources[agent_name][decorator_param] = parsed_value

        except ValueError:
            click.echo(
                f"Warning: Invalid value '{value}' for {flag_name}, expected {'integer' if resource_type in ['num-cpus', 'num-replicas', 'num-gpus'] else 'string'}"
            )

    return cli_resources


def _ensure_dependencies() -> bool:
    """Ensure Ray Serve dependencies are available."""
    try:
        import ray  # noqa: F401
        from fastapi import FastAPI  # noqa: F401
        from pydantic import BaseModel  # noqa: F401
        from ray import serve  # noqa: F401

        click.echo("Ray Serve dependencies available")
    except ImportError:
        click.echo("Installing Ray Serve dependencies...")
        try:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "ray[serve]",
                    "fastapi",
                    "uvicorn",
                ],
                check=True,
                capture_output=True,
            )
            click.echo("Ray Serve dependencies installed")
        except subprocess.CalledProcessError as e:
            click.echo(f"Failed to install Ray Serve: {e}")
            return False

    return True


def _discover_agents(project_dir: Path) -> dict[str, Any]:
    """Discover Agent classes in the agents/ directory."""
    agents: dict[str, Any] = {}
    agents_dir = project_dir / "agents"

    if not agents_dir.exists() or not agents_dir.is_dir():
        return agents

    for agent_folder in agents_dir.iterdir():
        if not agent_folder.is_dir() or agent_folder.name.startswith("__"):
            continue

        agent_file = agent_folder / "agent.py"
        if not agent_file.exists():
            click.echo(f"Warning: No agent.py found in {agent_folder.name}, skipping")
            continue

        agent_name = agent_folder.name
        agent_class = _load_agent_from_file(agent_file, f"agents.{agent_name}.agent")
        if agent_class:
            agents[agent_name] = {"class": agent_class, "file": agent_file}
        else:
            click.echo(f"Warning: No Agent class found in {agent_name}/agent.py")

    return agents


def _load_agent_from_file(file_path: Path, module_name: str) -> Any | None:
    """Load Agent class from a Python file."""
    try:
        project_dir = file_path.parent.parent
        if str(project_dir) not in sys.path:
            sys.path.insert(0, str(project_dir))

        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            click.echo(f"Failed to create module spec for {file_path}")
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        for _name, obj in inspect.getmembers(module, inspect.isclass):
            if obj.__module__ == module.__name__ and hasattr(obj, "run"):
                return obj

        if hasattr(module, "Agent"):
            return module.Agent

        click.echo(f"No agent class found in {file_path}")
        return None

    except Exception as e:
        click.echo(f"Failed to load agent from {file_path}: {e}")
        return None


def _select_agents(all_agents: dict[str, Any], agents: str) -> dict[str, Any]:
    """Select which agents to deploy."""
    if not agents:
        return all_agents

    agent_names = [name.strip() for name in agents.split(",")]
    selected = {}
    for name in agent_names:
        if name in all_agents:
            selected[name] = all_agents[name]
        else:
            click.echo(f"Agent '{name}' not found, skipping")
    return selected


def _create_chat_endpoint(app, agent_class: Any):
    """Create a single /chat endpoint for the agent."""
    from typing import Any

    from fastapi import HTTPException
    from pydantic import BaseModel

    class ChatRequest(BaseModel):
        data: dict[Any, Any]
        session_id: str = "default"

    class ChatResponse(BaseModel):
        result: dict[Any, Any]
        session_id: str

    @app.post("/chat", response_model=ChatResponse)
    async def chat_endpoint(request: ChatRequest):
        try:
            agent = agent_class()
            result = agent.run(request.data)
            return ChatResponse(result=result, session_id=request.session_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e


def _get_agent_resources_with_defaults(agent_class: Any) -> dict[str, Any]:
    """Get agent resources with sensible defaults if no decorator specified."""
    if has_resource_config(agent_class):
        resources = get_agent_resources(agent_class)
        click.echo(f"   Using custom resources: {resources}")
        return resources
    else:
        defaults = {"num_cpus": 1, "memory": "2GB", "num_replicas": 1, "num_gpus": 0}
        click.echo(f"   Using default resources: {defaults}")
        return defaults


def _merge_resources_with_cli_override(
    agent_class: Any,
    agent_name: str,
    cli_resources: dict[str, dict[str, Any]],
    deployed_agents: dict[str, Any],
) -> dict[str, Any]:
    """
    Merge CLI resource flags with decorator defaults using field-by-field precedence.

    Args:
        agent_class: Agent class (may have @ray_resources decorator)
        agent_name: Name of the agent
        cli_resources: Parsed CLI resource flags
        deployed_agents: Dict of agents being deployed (for validation)

    Returns:
        Final resource configuration with CLI overrides applied
    """
    if has_resource_config(agent_class):
        base_resources = get_agent_resources(agent_class).copy()
        source = "decorator"
    else:
        base_resources = {
            "num_cpus": 1,
            "memory": "2GB",
            "num_replicas": 1,
            "num_gpus": 0,
        }
        source = "defaults"

    cli_overrides = cli_resources.get(agent_name, {})

    if agent_name not in deployed_agents:
        if cli_overrides:
            for resource_key in cli_overrides.keys():
                flag_name = f"--{agent_name}-{resource_key.replace('_', '-')}"
                click.echo(
                    f"Warning: Resource flag '{flag_name}' specified for '{agent_name}' but '{agent_name}' not deployed"
                )
        return base_resources

    final_resources = base_resources.copy()
    overridden_fields = []

    for resource_key, cli_value in cli_overrides.items():
        if resource_key in final_resources:
            final_resources[resource_key] = cli_value
            overridden_fields.append(resource_key)
        else:
            click.echo(
                f"Warning: Unknown resource '{resource_key}' for agent '{agent_name}'"
            )

    if overridden_fields:
        click.echo(f"   Using {source} with CLI overrides: {overridden_fields}")
        click.echo(f"   Final resources: {final_resources}")
    else:
        click.echo(f"   Using {source}: {final_resources}")

    return final_resources


def _validate_cli_resource_flags(
    cli_resources: dict[str, dict[str, Any]], discovered_agents: dict[str, Any]
) -> None:
    """
    Warn about CLI resource flags for agents that don't exist.

    Args:
        cli_resources: Parsed CLI resource flags
        discovered_agents: Dict of discovered agents
    """
    for agent_name in cli_resources.keys():
        if agent_name not in discovered_agents:
            flags = []
            for resource_key in cli_resources[agent_name].keys():
                flag_name = f"--{agent_name}-{resource_key.replace('_', '-')}"
                flags.append(flag_name)

            click.echo(
                f"Warning: Resource flags {', '.join(flags)} reference unknown agent '{agent_name}'"
            )
            click.echo(f"   Available agents: {', '.join(discovered_agents.keys())}")


def _deploy_agents(
    agents: dict[str, Any], port: int, cli_resources: dict[str, dict[str, Any]]
):
    """Deploy agents on Ray Serve with single /chat endpoint."""
    try:
        import ray
        from fastapi import FastAPI
        from ray import serve

        click.echo("Initializing Ray...")

        if not ray.is_initialized():
            ray.init(ignore_reinit_error=True)

        serve.start(detached=True, http_options={"host": "0.0.0.0", "port": port})
        _validate_cli_resource_flags(cli_resources, agents)
        deployed_endpoints = []

        for agent_name, agent_info in agents.items():
            agent_class = agent_info["class"]

            if not hasattr(agent_class, "run"):
                click.echo(
                    f"Warning: Agent '{agent_name}' has no run() method, skipping"
                )
                continue

            click.echo(f"Configuring agent '{agent_name}':")
            resources = _merge_resources_with_cli_override(
                agent_class, agent_name, cli_resources, agents
            )

            ray_actor_options = {
                "num_cpus": resources["num_cpus"],
                "memory": resources["memory"],
            }
            if resources["num_gpus"] > 0:
                ray_actor_options["num_gpus"] = resources["num_gpus"]

            app = FastAPI(title=f"{agent_name} Agent")
            _create_chat_endpoint(app, agent_class)

            @serve.deployment(
                name=f"{agent_name}-deployment",
                num_replicas=resources["num_replicas"],
                ray_actor_options=ray_actor_options,
            )
            @serve.ingress(app)
            class AgentDeployment:
                def __init__(self, agent_cls=agent_class):
                    self.agent = agent_cls()

            deployment = AgentDeployment.bind()  # type: ignore
            serve.run(
                deployment,
                name=f"{agent_name}-service",
                route_prefix=f"/agents/{agent_name}",
            )

            endpoint_url = f"http://localhost:{port}/agents/{agent_name}/chat"
            deployed_endpoints.append((agent_name, endpoint_url, resources))

            gpu_info = (
                f", {resources['num_gpus']} GPUs" if resources["num_gpus"] > 0 else ""
            )
            click.echo(
                f"✓ Deployed '{agent_name}': {resources['num_replicas']} replicas, "
                f"{resources['num_cpus']} CPUs, {resources['memory']}{gpu_info}"
            )

        if deployed_endpoints:
            click.echo(
                f"\nSuccessfully deployed {len(deployed_endpoints)} endpoint(s):"
            )
            for agent_name, endpoint_url, _resources in deployed_endpoints:
                click.echo(f"\n{agent_name}:")
                click.echo(f"  Endpoint: POST {endpoint_url}")
                click.echo(f"  Test it:  curl -X POST {endpoint_url} \\")
                click.echo("                 -H 'Content-Type: application/json' \\")
                json_data = '{"data": {"message": "hello"}, "session_id": "test"}'
                click.echo(f"                 -d '{json_data}'")

            click.echo("\nRay Dashboard: http://localhost:8265")
            click.echo("Press Ctrl+C to stop all agents")

            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                click.echo("\nShutting down agents...")
                serve.shutdown()
                ray.shutdown()
                click.echo("All agents stopped")
        else:
            click.echo("No agents were deployed")
            serve.shutdown()
            ray.shutdown()

    except Exception as e:
        click.echo(f"Failed to deploy agents: {e}")
        try:
            serve.shutdown()
            ray.shutdown()
        except Exception:
            pass
