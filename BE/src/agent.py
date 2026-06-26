import asyncio
from datetime import datetime, timedelta
import uuid

from agentscope.agent import ReActAgent
from agentscope.message import Msg, ToolUseBlock, ToolResultBlock
from agentscope.model import OpenAIChatModel  # DeepSeek 兼容 OpenAI API
from agentscope.formatter import OpenAIChatFormatter
from agentscope.memory import InMemoryMemory
from agentscope.tool import (
    Toolkit,
    view_text_file,
    write_text_file,
    insert_text_file,
)
from config import Config
from prompt_loader import (
    load_agent_prompt,
    get_memory_context_prompt,
)
from runtime_config import (
    AgentRuntimeConfig,
    load_agent_runtime_config,
    register_configured_mcp_clients,
    register_configured_skills,
)
from tools.agent_browser import agent_browser
from tools.sub_agent_tools import (
    sales_agent_tool,
    technical_agent_tool,
    production_agent_tool,
)
from typing import Dict, Optional


TOOL_FUNCTIONS = {
    "view_text_file": view_text_file,
    "write_text_file": write_text_file,
    "insert_text_file": insert_text_file,
    "agent_browser": agent_browser,
    "sales_agent_tool": sales_agent_tool,
    "technical_agent_tool": technical_agent_tool,
    "production_agent_tool": production_agent_tool,
}

def _build_sys_prompt(role: str) -> str:
    """构建完整的系统提示词：人设 + 技能提示 + memory 路径上下文"""
    persona = load_agent_prompt(role)
    memory_ctx = get_memory_context_prompt(role)
    return persona + memory_ctx


def _register_tool_functions(toolkit: Toolkit, config: AgentRuntimeConfig) -> None:
    unknown = sorted(set(config.tools) - set(TOOL_FUNCTIONS))
    if unknown:
        raise ValueError(
            f"Unknown tool(s): {unknown}. Available tools: {sorted(TOOL_FUNCTIONS)}"
        )

    for tool_name in config.tools:
        toolkit.register_tool_function(TOOL_FUNCTIONS[tool_name])


async def _create_toolkit(role: str) -> Toolkit:
    """创建并配置 Toolkit，按 agent 配置注册工具、MCP 和技能"""
    toolkit = Toolkit()
    runtime_config = load_agent_runtime_config(role)

    _register_tool_functions(toolkit, runtime_config)
    await register_configured_mcp_clients(
        toolkit,
        runtime_config,
        strict=Config.MCP_STRICT_REGISTRATION,
    )
    register_configured_skills(toolkit, runtime_config)

    return toolkit


class MetatoolReActAgent(ReActAgent):
    """ReActAgent 子类，将 ToolResponse 的 metadata 保存到 Msg.metadata 上，
    以便流式输出时能传递给前端。"""

    async def _acting(self, tool_call: ToolUseBlock) -> dict | None:
        """与父类相同，但将 ToolResponse.metadata 复制到打印的 Msg 上。"""
        tool_res_msg = Msg(
            "system",
            [
                ToolResultBlock(
                    type="tool_result",
                    id=tool_call["id"],
                    name=tool_call["name"],
                    output=[],
                ),
            ],
            "system",
        )
        try:
            tool_res = await self.toolkit.call_tool_function(tool_call)

            async for chunk in tool_res:
                tool_res_msg.content[0]["output"] = chunk.content
                # 将 ToolResponse 的 metadata 保存到 Msg 上
                if chunk.metadata:
                    tool_res_msg.metadata = chunk.metadata

                await self.print(tool_res_msg, chunk.is_last)

                if chunk.is_interrupted:
                    raise asyncio.CancelledError()

                if (
                    tool_call["name"] == self.finish_function_name
                    and chunk.metadata
                    and chunk.metadata.get("success", False)
                ):
                    return chunk.metadata.get("structured_output")

            return None

        finally:
            await self.memory.add(tool_res_msg)


class AgentSession:
    """持有 Agent 实例的会话。使用 async factory 模式创建，
    因为 MCP 工具注册是异步的。"""

    def __init__(self):
        """请使用 AgentSession.create() 异步工厂方法创建实例。"""
        self.session_id: str = ""
        self.user_id: str = ""
        self.created_at: datetime = datetime.now()
        self.last_accessed: datetime = datetime.now()
        self.default_role: str = ""
        self.agents: Dict[str, MetatoolReActAgent] = {}

    @classmethod
    async def create(cls, session_id: str, user_id: str, default_role: str) -> "AgentSession":
        """异步工厂方法：创建 AgentSession 并初始化默认 Agent。

        Args:
            session_id: 会话唯一标识
            user_id: 用户标识
            default_role: 默认 agent 角色

        Returns:
            初始化完成的 AgentSession 实例
        """
        self = cls.__new__(cls)
        self.session_id = session_id
        self.user_id = user_id
        self.created_at = datetime.now()
        self.last_accessed = datetime.now()
        self.default_role = default_role
        self.agents = {}

        return self

    async def get_agent(self, role: str | None = None) -> MetatoolReActAgent:
        """获取指定角色的 Agent；不存在时按角色配置懒加载创建。"""
        agent_role = role or self.default_role
        if agent_role in self.agents:
            return self.agents[agent_role]

        toolkit = await _create_toolkit(agent_role)

        sys_prompt = _build_sys_prompt(agent_role)
        skill_prompt = toolkit.get_agent_skill_prompt()
        if skill_prompt:
            sys_prompt += "\n\n" + skill_prompt

        agent = MetatoolReActAgent(
            name=f"Agent_{self.user_id}_{agent_role}",
            model=OpenAIChatModel(
                model_name=Config.MODEL_NAME,
                api_key=Config.DEEPSEEK_API_KEY,
                client_kwargs={
                    "base_url": Config.DEEPSEEK_BASE_URL,
                    "timeout": 60,
                    "max_retries": 3,
                },
                stream=True,
            ),
            sys_prompt=sys_prompt,
            memory=InMemoryMemory(),
            toolkit=toolkit,
            formatter=OpenAIChatFormatter(),
        )
        agent.set_console_output_enabled(True)
        self.agents[agent_role] = agent
        return agent

    def is_expired(self) -> bool:
        return datetime.now() - self.last_accessed > timedelta(hours=Config.SESSION_EXPIRE_HOURS)

    def touch(self):
        self.last_accessed = datetime.now()


class SessionManager:
    def __init__(self):
        self._sessions: Dict[str, AgentSession] = {}
        self._api_key_to_sessions: Dict[str, set] = {}  # 一个 api_key 可以有多个 session

    async def create_session(self, api_key: str, user_id: str, default_role: str) -> AgentSession:
        session_id = str(uuid.uuid4())
        session = await AgentSession.create(session_id, user_id, default_role)
        self._sessions[session_id] = session
        if api_key not in self._api_key_to_sessions:
            self._api_key_to_sessions[api_key] = set()
        self._api_key_to_sessions[api_key].add(session_id)
        return session

    def get_session(self, session_id: str) -> Optional[AgentSession]:
        session = self._sessions.get(session_id)
        if session and session.is_expired():
            self.remove_session(session_id)
            return None
        if session:
            session.touch()
        return session

    def remove_session(self, session_id: str):
        if session_id in self._sessions:
            del self._sessions[session_id]
            for api_key, session_ids in self._api_key_to_sessions.items():
                if session_id in session_ids:
                    session_ids.discard(session_id)
                    if not session_ids:
                        del self._api_key_to_sessions[api_key]
                    break

    def get_active_count(self) -> int:
        return len(self._sessions)

    def cleanup_expired_sessions(self):
        """清理所有过期 Session"""
        expired_sessions = [
            sid for sid, s in self._sessions.items() if s.is_expired()
        ]
        for session_id in expired_sessions:
            self.remove_session(session_id)
        return len(expired_sessions)
