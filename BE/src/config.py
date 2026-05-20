# ==================== 配置 ====================
import os
from pathlib import Path

# 加载 .env 文件（BE/.env）
from dotenv import load_dotenv
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)


class Config:
    # DeepSeek 配置（通过 OpenAI 兼容接口）
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")  # 加上 /v1
    MODEL_NAME = os.getenv("MODEL_NAME", "deepseek-chat")
    PORT = int(os.getenv("PORT", 8080))
    # Agent 角色：对应 agents/ 目录下的子文件夹名
    AGENT_ROLE = os.getenv("AGENT_ROLE", "default")
    
    # 前端认证 Key
    VALID_API_KEYS = {
        "sk-frontend-001": {"user_id": "user_001", "expire_days": 30},
        "sk-frontend-002": {"user_id": "user_002", "expire_days": 30},
    }
    
    # Session 配置
    SESSION_EXPIRE_HOURS = 24  # 24 小时过期