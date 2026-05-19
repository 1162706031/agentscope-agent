
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from agent import SessionManager
from config import Config
from agentscope.message import Msg



class AuthRequest(BaseModel):
    api_key: str

class AuthResponse(BaseModel):
    session_id: str
    user_id: str
    expires_at: str

class ChatRequest(BaseModel):
    session_id: str
    message: str = ""  # 简化：单条消息，logout 不需要 message

class ChatResponse(BaseModel):
    session_id: str
    content: str
    role: str


# ==================== FastAPI 应用 ====================
session_manager = SessionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("AgentScope Agent starting...")
    async def cleanup_loop():
        while True:
            await asyncio.sleep(3600)  # 每小时执行一次
            session_manager.cleanup_expired_sessions()
            print(f"Cleanup done. Active sessions: {session_manager.get_active_count()}")
    
    task = asyncio.create_task(cleanup_loop())
    yield
    task.cancel()
    print("AgentScope Agent shutting down...")

app = FastAPI(lifespan=lifespan)


def verify_api_key(api_key: str) -> dict:
    if api_key not in Config.VALID_API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return {"user_id": Config.VALID_API_KEYS[api_key]["user_id"]}


# ==================== API 端点 ====================
@app.get("/health")
async def health():
    return {"status": "healthy", "active_sessions": session_manager.get_active_count()}


@app.post("/auth", response_model=AuthResponse)
async def authenticate(request: AuthRequest):
    """首次认证：传入 API Key 返回 session_id"""
    user_info = verify_api_key(request.api_key)
    session = session_manager.create_session(request.api_key, user_info["user_id"])
    
    expires_at = datetime.now() + timedelta(hours=Config.SESSION_EXPIRE_HOURS)
    return AuthResponse(
        session_id=session.session_id,
        user_id=user_info["user_id"],
        expires_at=expires_at.isoformat()
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """对话：使用 session_id 复用 Agent"""
    session = session_manager.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Session expired, please re-authenticate")
    
    # 构建 AgentScope 消息格式
    user_msg = Msg(name="user", role="user", content=request.message)

    # 调用 Agent（非流式）
    response = await session.agent(user_msg)

    content = response.get_text_content() if response else "No response"
    
    return ChatResponse(
        session_id=session.session_id,
        content=content,
        role="assistant"
    )


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """流式对话：使用 session_id，复用 Agent"""
    session = session_manager.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Session expired, please re-authenticate")
    
    user_msg = Msg(name="user", role="user", content=request.message)

    async def generate():
        response = await session.agent(user_msg)
        if response:
            text = response.get_text_content()
            if text:
                yield f"data: {text}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/logout")
async def logout(request: ChatRequest):
    """主动销毁会话"""
    session_manager.remove_session(request.session_id)
    return {"status": "logged out"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=Config.PORT)