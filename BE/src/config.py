# ==================== 配置 ====================
import os
from pathlib import Path

# 加载 .env 文件（BE/.env） ////测试的时候加上
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False

_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)


def _split_roles(value: str) -> list[str]:
    return [role.strip() for role in value.split(",") if role.strip()]


class Config:
    # DeepSeek 配置（通过 OpenAI 兼容接口）
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    MODEL_NAME = os.getenv("MODEL_NAME", "deepseek-chat")
    PORT = int(os.getenv("PORT", 8080))
    # 默认 Agent 角色：对应 agents/ 目录下的子文件夹名
    _agent_role_env = os.getenv("AGENT_ROLE", "Webassistance")
    _agent_roles_env = os.getenv("AGENT_ROLES")
    _agent_role_parts = _split_roles(_agent_role_env)
    AGENT_ROLE = _agent_role_parts[0] if _agent_role_parts else "Webassistance"
    # 可启用的 Agent 角色列表，逗号分隔；未设置时兼容旧配置，支持 AGENT_ROLE 写成逗号列表
    AGENT_ROLES = _split_roles(_agent_roles_env) if _agent_roles_env else _agent_role_parts
    MCP_STRICT_REGISTRATION = os.getenv(
        "MCP_STRICT_REGISTRATION",
        "false",
    ).lower() in {"1", "true", "yes", "on"}

    # 模型信息（根据 MODEL_NAME 自动设置）
    MODEL_INFO = {
        "deepseek-chat": {"provider": "DeepSeek", "description": "DeepSeek Chat", "max_context_length": 65536},
        "deepseek-coder": {"provider": "DeepSeek", "description": "DeepSeek Coder", "max_context_length": 65536},
        "deepseek-v3": {"provider": "DeepSeek", "description": "DeepSeek V3", "max_context_length": 65536},
        "deepseek-r1": {"provider": "DeepSeek", "description": "DeepSeek R1", "max_context_length": 65536},
    }

    @classmethod
    def get_model_info(cls) -> dict:
        """获取当前模型的详细信息"""
        info = cls.MODEL_INFO.get(cls.MODEL_NAME, {
            "provider": "Unknown",
            "description": cls.MODEL_NAME,
            "max_context_length": 4096,
        })
        return {
            "name": cls.MODEL_NAME,
            "provider": info["provider"],
            "description": info["description"],
            "max_context_length": info["max_context_length"],
            "base_url": cls.DEEPSEEK_BASE_URL,
        }

    # 前端认证 Key
    VALID_API_KEYS = {
        "sk-frontend-001": {"user_id": "user_001", "expire_days": 30},
        "sk-frontend-002": {"user_id": "user_002", "expire_days": 30},
    }

    # Session 配置
    SESSION_EXPIRE_HOURS = 24  # 24 小时过期
