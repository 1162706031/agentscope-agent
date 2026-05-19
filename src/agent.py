from datetime import datetime, timedelta
import uuid

from agentscope.agent import ReActAgent
from agentscope.model import OpenAIChatModel  # DeepSeek 兼容 OpenAI API
from agentscope.formatter import OpenAIChatFormatter
from agentscope.memory import InMemoryMemory
from config import Config
from typing import Dict, Optional


class AgentSession:
    """持有 Agent 实例的会话"""

    def __init__(self, session_id: str, user_id: str):
        self.session_id = session_id
        self.user_id = user_id
        self.created_at = datetime.now()
        self.last_accessed = datetime.now()

        # 创建 Agent 实例（每个会话复用）
        self.agent = ReActAgent(
            name=f"Agent_{user_id}",
            model=OpenAIChatModel(
                model_name=Config.MODEL_NAME,
                api_key=Config.DEEPSEEK_API_KEY,
                client_kwargs={
                    "base_url": Config.DEEPSEEK_BASE_URL,
                    # 或其他 OpenAI 客户端支持的参数
                    "timeout": 60,
                    "max_retries": 3
                },
                stream=True,
            ),
            sys_prompt="你是一个乐于助人的好帮手，协助用户解答问题。要用中文回答。",
            memory=InMemoryMemory(),
            formatter=OpenAIChatFormatter(),
        )
        self.agent.set_console_output_enabled(False)

    def is_expired(self) -> bool:
        return datetime.now() - self.last_accessed > timedelta(hours=Config.SESSION_EXPIRE_HOURS)

    def touch(self):
        self.last_accessed = datetime.now()


class SessionManager:
    def __init__(self):
        self._sessions: Dict[str, AgentSession] = {}
        self._api_key_to_session: Dict[str, str] = {}

    def create_session(self, api_key: str, user_id: str) -> AgentSession:
        if api_key in self._api_key_to_session:
            old_id = self._api_key_to_session[api_key]
            self._sessions.pop(old_id, None)
            del self._api_key_to_session[api_key]

        session_id = str(uuid.uuid4())
        session = AgentSession(session_id, user_id)
        self._sessions[session_id] = session
        self._api_key_to_session[api_key] = session_id
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
            keys_to_remove = [k for k, v in self._api_key_to_session.items() if v == session_id]
            for k in keys_to_remove:
                del self._api_key_to_session[k]

    def get_active_count(self) -> int:
        return len(self._sessions)

    def cleanup_expired_sessions(self):
        """清理所有过期 Session"""
        expired_sessions = []
        for session_id, session in self._sessions.items():
            if session.is_expired():
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            self.remove_session(session_id)

        return len(expired_sessions)
