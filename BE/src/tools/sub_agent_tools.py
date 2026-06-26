# -*- coding: utf-8 -*-
"""Sub-agent tools for the Xufeng Material intelligent customer service system.

Three stateless specialist agent tools, each powered by a temporary ReActAgent:
- sales_agent_tool: Product recommendation, pricing, quotation, inventory
- technical_agent_tool: Failure analysis, heat treatment, material comparison
- production_agent_tool: Manufacturing process, quality control, production cycle

Each sub-agent tool spawns a short-lived ReActAgent with its own mini Toolkit:
- tools, MCP clients, and skills declared in agents/{role}/CONFIG.json

Stateless: ReActAgent + Toolkit live only during the tool call.
No persistent agent instance, no conversation memory between calls.
"""
import asyncio

from agentscope.agent import ReActAgent
from agentscope.model import OpenAIChatModel
from agentscope.memory import InMemoryMemory
from agentscope.formatter import OpenAIChatFormatter
from agentscope.message import Msg, TextBlock, ToolUseBlock, ToolResultBlock
from agentscope.tool import (
    Toolkit,
    ToolResponse,
    view_text_file,
    write_text_file,
    insert_text_file,
)
from config import Config
from prompt_loader import load_agent_prompt, get_memory_path
from runtime_config import (
    AgentRuntimeConfig,
    load_agent_runtime_config,
    register_configured_mcp_clients,
    register_configured_skills,
)


class _SubReActAgent(ReActAgent):
    """ReActAgent with fixed _acting() that creates a proper Msg object
    instead of a tuple. The vanilla library version has a bug where
    tool_res_msg is a tuple, causing 'str' object has no attribute 'id'
    when memory.add() iterates over it."""

    async def _acting(self, tool_call: ToolUseBlock) -> dict | None:
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


# ==================== Shared Model ====================

_model: OpenAIChatModel | None = None


def _get_model() -> OpenAIChatModel:
    """Lazy-init shared OpenAIChatModel (stateless, can be reused across calls)."""
    global _model
    if _model is None:
        _model = OpenAIChatModel(
            model_name=Config.MODEL_NAME,
            api_key=Config.DEEPSEEK_API_KEY,
            client_kwargs={
                "base_url": Config.DEEPSEEK_BASE_URL,
                "timeout": 60,
                "max_retries": 2,
            },
            stream=False,  # Internal tool call, no streaming needed
        )
    return _model


# ==================== Sub-Agent Toolkit Factory ====================

SUB_AGENT_TOOL_FUNCTIONS = {
    "view_text_file": view_text_file,
    "write_text_file": write_text_file,
    "insert_text_file": insert_text_file,
}


def _register_sub_agent_tool_functions(
    toolkit: Toolkit,
    config: AgentRuntimeConfig,
) -> None:
    unknown = sorted(set(config.tools) - set(SUB_AGENT_TOOL_FUNCTIONS))
    if unknown:
        raise ValueError(
            f"Unknown sub-agent tool(s): {unknown}. Available tools: "
            f"{sorted(SUB_AGENT_TOOL_FUNCTIONS)}"
        )

    for tool_name in config.tools:
        toolkit.register_tool_function(SUB_AGENT_TOOL_FUNCTIONS[tool_name])


async def _build_sub_agent_toolkit(role: str) -> Toolkit:
    """Build a mini Toolkit for a sub-agent.

    Each sub-agent gets only the tools, MCP clients, and skills declared in
    agents/{role}/CONFIG.json.
    """
    toolkit = Toolkit()
    runtime_config = load_agent_runtime_config(role)

    _register_sub_agent_tool_functions(toolkit, runtime_config)
    await register_configured_mcp_clients(toolkit, runtime_config)
    register_configured_skills(toolkit, runtime_config)

    return toolkit


# ==================== Sub-Agent Runner ====================

async def _run_sub_agent(role: str, question: str, context: str = "") -> str:
    """Run a sub-agent using AgentScope's native ReActAgent.

    This is a stateless, single-question call:
    1. Build toolkit from agents/{role}/CONFIG.json
    2. Load specialist system prompt
    3. Create a temporary ReActAgent
    4. Send the question, wait for final answer
    5. Discard the agent (no state persists between calls)

    Args:
        role: Agent role name (sales, technical-engineer, production)
        question: The user's question
        context: Optional additional context (e.g. pre-searched info)

    Returns:
        The sub-agent's final text answer
    """
    toolkit = await _build_sub_agent_toolkit(role)

    # Build system prompt (PROFILE + SOUL + AGENTS)
    system_prompt = load_agent_prompt(role)

    # Inject memory file path context so memory skill writes to the right file
    memory_path = get_memory_path(role)
    if memory_path:
        system_prompt += (
            f"\n\n## 长期记忆文件\n"
            f"当前角色的长期记忆文件路径为：`{memory_path}`\n"
            f"当需要记录或查阅长期记忆时，请使用 memory 技能操作此文件。"
        )

    # Build user message
    user_content = f"【用户问题】\n{question}"
    if context:
        user_content += f"\n\n【参考资料（来自web搜索）】\n{context}"

    agent = _SubReActAgent(
        name=f"SubAgent_{role}",
        model=_get_model(),
        sys_prompt=system_prompt,
        memory=InMemoryMemory(),
        toolkit=toolkit,
        formatter=OpenAIChatFormatter(),
    )

    try:
        msg = Msg("user", user_content, "user")
        reply = await agent(msg)
        return reply.get_text_content() or "[智能体未生成回复]"
    except Exception as e:
        return f"[智能体调用出错] role={role}, error={e}"


# ==================== Sales Agent Tool ====================

async def sales_agent_tool(
    question: str,
    context: str = "",
) -> ToolResponse:
    """Sales specialist for Xufeng New Material (旭丰新材料) — product
    recommendation, pricing analysis, inventory inquiry, quotation generation.

    Spawns a temporary ReActAgent with web-search MCP + memory skill,
    runs a tool-calling loop, and returns the final answer.

    Call this tool when the user asks about:
    - Product pricing, market prices, cost breakdown
    - Which steel grade to choose for a specific application
    - Inventory availability, delivery time
    - Quotation requests, purchase intention
    - Budget estimation, cost-performance comparison

    Args:
        question:
            The user's question, analyzed and refined by the main agent.
            Include all relevant details: application scenario, quantity,
            quality requirements, budget constraints, etc.
        context:
            Optional. Pre-searched information the main agent gathered.
            The sub-agent can also search on its own via its web_search tool.

    Returns:
        ToolResponse with the specialist's answer.
    """
    answer = await _run_sub_agent("sales", question, context)
    return ToolResponse(
        content=[TextBlock(type="text", text=answer)],
        is_last=True,
    )


# ==================== Technical Engineer Tool ====================

async def technical_agent_tool(
    question: str,
    context: str = "",
) -> ToolResponse:
    """Technical / materials engineer for Xufeng New Material (旭丰新材料) —
    failure analysis, heat treatment recommendation, material property
    comparison, crack analysis, hardness issue diagnosis.

    Spawns a temporary ReActAgent with web-search MCP + memory skill,
    runs a tool-calling loop, and returns the final answer.

    Call this tool when the user asks about:
    - Why a mold cracked / broke / failed
    - Heat treatment process parameters (quenching, tempering, annealing)
    - Material property comparison between grades (e.g. DC53 vs SKD11)
    - Hardness issues (too high, too low, uneven)
    - Material selection based on technical requirements
    - Wear resistance, thermal fatigue, corrosion analysis

    Args:
        question:
            The user's technical question with all relevant context:
            application, failure mode, current parameters, etc.
        context:
            Optional. Pre-searched information the main agent gathered.
            The sub-agent can also search on its own via its web_search tool.

    Returns:
        ToolResponse with the specialist's technical analysis.
    """
    answer = await _run_sub_agent("technical-engineer", question, context)
    return ToolResponse(
        content=[TextBlock(type="text", text=answer)],
        is_last=True,
    )


# ==================== Production Agent Tool ====================

async def production_agent_tool(
    question: str,
    context: str = "",
) -> ToolResponse:
    """Production process specialist for Xufeng New Material (旭丰新材料) —
    manufacturing process explanation, process flow validation, abnormal
    parameter alerts, production record generation, delivery time estimation.

    Spawns a temporary ReActAgent with web-search MCP + memory skill,
    runs a tool-calling loop, and returns the final answer.

    Call this tool when the user asks about:
    - Manufacturing process: EAF → LF → VD → ESR → Forging → Annealing
    - Process parameters and quality control points
    - Whether a specific process flow is correct
    - Abnormal parameter diagnosis and troubleshooting
    - Production cycle and delivery time estimation
    - Equipment specifications and capabilities

    Args:
        question:
            The user's production-related question with relevant context.
        context:
            Optional. Pre-searched information the main agent gathered.
            The sub-agent can also search on its own via its web_search tool.

    Returns:
        ToolResponse with the specialist's production analysis.
    """
    answer = await _run_sub_agent("production", question, context)
    return ToolResponse(
        content=[TextBlock(type="text", text=answer)],
        is_last=True,
    )
