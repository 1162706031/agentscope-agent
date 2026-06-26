
import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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
            print(
                f"Cleanup done. Active sessions: {session_manager.get_active_count()}")

    task = asyncio.create_task(cleanup_loop())
    yield
    task.cancel()
    print("AgentScope Agent shutting down...")

app = FastAPI(lifespan=lifespan)

# CORS 配置（允许前端开发时的跨域请求）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_api_key(api_key: str) -> dict:
    if api_key not in Config.VALID_API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return {"user_id": Config.VALID_API_KEYS[api_key]["user_id"]}


# ==================== API 端点 ====================
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "active_sessions": session_manager.get_active_count(),
        "model": Config.get_model_info(),
        "agent_role": Config.AGENT_ROLE,
        "port": Config.PORT,
    }


@app.post("/auth", response_model=AuthResponse)
async def authenticate(request: AuthRequest):
    """首次认证：传入 API Key 返回 session_id"""
    user_info = verify_api_key(request.api_key)
    session = await session_manager.create_session(
        request.api_key, user_info["user_id"])

    expires_at = datetime.now() + timedelta(hours=Config.SESSION_EXPIRE_HOURS)
    return AuthResponse(
        session_id=session.session_id,
        user_id=user_info["user_id"],
        expires_at=expires_at.isoformat()
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """对话：使用 session_id 复用 Agent，同步等待完整回复"""
    session = session_manager.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    msg = Msg("user", request.message, "user")
    reply = await session.agent(msg)

    return ChatResponse(
        session_id=request.session_id,
        content=reply.get_text_content() or "",
        role="assistant",
    )


@app.post("/chat/stream", response_class=StreamingResponse)
async def chat_stream(request: ChatRequest):
    """流式对话：通过 msg_queue 实时推送 Agent 生成的文本"""
    session = session_manager.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    agent = session.agent
    # 为每个流式请求创建独立队列，避免残留消息干扰
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    agent.set_msg_queue_enabled(True, queue=queue)

    async def event_generator():
        msg = Msg("user", request.message, "user")
        task = asyncio.create_task(agent(msg))
        sent_by_msg: dict[str, str] = {}
        sent_actions = set()

        async def emit_msg(msg_obj: Msg):
            """发送一条消息的 action 和 text 到 SSE"""
            if msg_obj.metadata and isinstance(msg_obj.metadata, dict):
                action = msg_obj.metadata.get("action")
                payload = msg_obj.metadata.get("payload")
                if action and payload:
                    action_key = f"{action}:{payload.get('url', '')}"
                    if action_key not in sent_actions:
                        sent_actions.add(action_key)
                        yield f"data: {json.dumps({'type': 'action', 'action': action, 'payload': payload}, ensure_ascii=False)}\n\n"

            text = msg_obj.get_text_content() or ""
            if not text:
                return

            msg_id = msg_obj.id or ""
            prev = sent_by_msg.get(msg_id, "")
            if text != prev:
                sent_by_msg[msg_id] = text
                yield f"data: {json.dumps({'type': 'text', 'msg_id': msg_id, 'content': text}, ensure_ascii=False)}\n\n"

        try:
            while True:
                try:
                    msg_obj, _, _ = await asyncio.wait_for(
                        queue.get(), timeout=0.05
                    )
                    async for data in emit_msg(msg_obj):
                        yield data
                except asyncio.TimeoutError:
                    if task.done():
                        break
                    continue

            try:
                reply = await task
                async for data in emit_msg(reply):
                    yield data
            except Exception as e:
                yield f"data: {json.dumps({'type': 'text', 'content': f'错误: {e}'}, ensure_ascii=False)}\n\n"
        except asyncio.CancelledError:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/logout")
async def logout(request: ChatRequest):
    """主动销毁会话"""
    session_manager.remove_session(request.session_id)
    return {"status": "logged out"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=Config.PORT)
