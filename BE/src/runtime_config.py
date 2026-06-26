import json
from dataclasses import dataclass
from typing import Any

from prompt_loader import AGENTS_DIR, SKILLS_DIR


CONFIG_FILENAME = "CONFIG.json"


def _get_web_search_mcp_client() -> Any:
    try:
        from Mcp.All_mcp import _get_web_search_client
    except ImportError:
        from BE.src.Mcp.All_mcp import _get_web_search_client
    return _get_web_search_client()


def _get_texttosql_mcp_client() -> Any:
    try:
        from Mcp.All_mcp import _get_texttosql
    except ImportError:
        from BE.src.Mcp.All_mcp import _get_texttosql
    return _get_texttosql()


MCP_CLIENT_FACTORIES = {
    "web_search": _get_web_search_mcp_client,
    "texttosql": _get_texttosql_mcp_client,
}


@dataclass(frozen=True)
class AgentRuntimeConfig:
    tools: tuple[str, ...]
    mcps: tuple[str, ...]
    skills: tuple[str, ...]


def _read_string_list(data: dict[str, Any], key: str, role: str) -> tuple[str, ...]:
    value = data.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(
            f"{CONFIG_FILENAME} for role '{role}' field '{key}' must be a list of strings"
        )
    return tuple(value)


def load_agent_runtime_config(role: str) -> AgentRuntimeConfig:
    """Load tools/MCP/skills allowlist for an agent role."""
    role_dir = AGENTS_DIR / role
    config_path = role_dir / CONFIG_FILENAME

    if not config_path.is_file():
        raise FileNotFoundError(
            f"Agent config for role '{role}' not found at {config_path}"
        )

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {config_path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"{config_path} must contain a JSON object")

    return AgentRuntimeConfig(
        tools=_read_string_list(data, "tools", role),
        mcps=_read_string_list(data, "mcps", role),
        skills=_read_string_list(data, "skills", role),
    )


async def register_configured_mcp_clients(toolkit: Any, config: AgentRuntimeConfig) -> None:
    unknown = sorted(set(config.mcps) - set(MCP_CLIENT_FACTORIES))
    if unknown:
        raise ValueError(
            f"Unknown MCP client(s): {unknown}. Available MCP clients: "
            f"{sorted(MCP_CLIENT_FACTORIES)}"
        )

    for mcp_name in config.mcps:
        await toolkit.register_mcp_client(MCP_CLIENT_FACTORIES[mcp_name]())


def register_configured_skills(toolkit: Any, config: AgentRuntimeConfig) -> None:
    unknown = []
    for skill_name in config.skills:
        skill_dir = SKILLS_DIR / skill_name
        if not skill_dir.is_dir():
            unknown.append(skill_name)
            continue
        toolkit.register_agent_skill(str(skill_dir))

    if unknown:
        raise ValueError(
            f"Unknown skill(s): {sorted(unknown)}. Available skills: "
            f"{list_available_skills()}"
        )


def list_available_skills() -> list[str]:
    if not SKILLS_DIR.is_dir():
        return []
    return sorted(
        path.name
        for path in SKILLS_DIR.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    )
