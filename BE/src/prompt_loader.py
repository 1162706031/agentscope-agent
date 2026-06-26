import os
from pathlib import Path


AGENTS_DIR = Path(__file__).parent.parent / "agents"
SKILLS_DIR = Path(__file__).parent.parent / "skills"

# 默认加载到系统提示词的文件（按此顺序拼接）
PROMPT_FILES = ["PROFILE.md", "SOUL.md", "AGENTS.md"]

# 不加载到系统提示词的文件
NON_PROMPT_FILES = ["MEMORY.md", "BOOTSTRAP.md", "CONFIG.json"]


def load_agent_prompt(role: str) -> str:
    """根据角色名加载人设文件，拼接为系统提示词。

    Args:
        role: 角色名，对应 agents/ 下的子文件夹名

    Returns:
        拼接后的系统提示词字符串
    """
    role_dir = AGENTS_DIR / role

    if not role_dir.is_dir():
        raise FileNotFoundError(
            f"Agent role '{role}' not found at {role_dir}. "
            f"Available roles: {list_available_roles()}"
        )

    parts = []
    for filename in PROMPT_FILES:
        filepath = role_dir / filename
        if filepath.is_file():
            content = filepath.read_text(encoding="utf-8").strip()
            if content:
                parts.append(content)

    if not parts:
        raise ValueError(f"No prompt files found for role '{role}'")

    return "\n\n---\n\n".join(parts)


def list_available_roles() -> list[str]:
    """列出所有可用的 agent 角色"""
    if not AGENTS_DIR.is_dir():
        return []
    return sorted(
        d.name
        for d in AGENTS_DIR.iterdir()
        if d.is_dir() and not d.name.startswith(".") and not d.name.startswith("_")
    )


def get_memory_path(role: str) -> str | None:
    """获取角色的 MEMORY.md 绝对路径"""
    filepath = (AGENTS_DIR / role / "MEMORY.md").resolve()
    if filepath.is_file():
        return str(filepath)
    return None


def get_memory_context_prompt(role: str) -> str:
    """生成 MEMORY.md 路径上下文，注入到系统提示词中，
    让 agent 知道记忆文件的位置。

    Args:
        role: 角色名

    Returns:
        memory 路径上下文文本
    """
    memory_path = get_memory_path(role)
    if memory_path:
        return (
            f"\n\n## 长期记忆文件\n"
            f"当前角色的长期记忆文件路径为：`{memory_path}`\n"
            f"当需要记录或查阅长期记忆时，请使用 memory 技能操作此文件。"
        )
    return ""
