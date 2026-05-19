# ==================== 配置 ====================
import os


class Config:
    # DeepSeek 配置（通过 OpenAI 兼容接口）
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")  # 加上 /v1
    MODEL_NAME = os.getenv("MODEL_NAME", "deepseek-chat")
    PORT = int(os.getenv("PORT", 8080))
    
    # 前端认证 Key
    VALID_API_KEYS = {
        "sk-frontend-001": {"user_id": "user_001", "expire_days": 30},
        "sk-frontend-002": {"user_id": "user_002", "expire_days": 30},
    }
    
    # Session 配置
    SESSION_EXPIRE_HOURS = 24  # 24 小时过期