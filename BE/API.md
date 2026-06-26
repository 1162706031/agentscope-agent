# AgentScope Agent — API 接口文档

**Base URL:** `http://localhost:8080`

---

## 1. Health Check

```
GET /health
```

**用途：** 健康检查，返回服务状态和活跃会话数。

**请求示例：**

```bash
curl http://localhost:8080/health
```

**响应示例：**

```json
{
  "status": "healthy",
  "active_sessions": 3,
  "default_agent_role": "Webassistance",
  "enabled_agent_roles": ["Webassistance", "internal-assistant"]
}
```

---

## 2. Agent 列表

```
GET /agents
```

**用途：** 返回当前服务可选择的 Agent 角色。`enabled_agent_roles` 由环境变量 `AGENT_ROLES` 控制；未设置时只启用 `AGENT_ROLE`。

**响应示例：**

```json
{
  "default_agent_role": "Webassistance",
  "enabled_agent_roles": ["Webassistance", "internal-assistant"],
  "available_agent_roles": ["Webassistance", "coder", "default", "internal-assistant", "production", "sales", "technical-engineer"]
}
```

---

## 3. 认证 / 创建会话

```
POST /auth
```

**用途：** 传入 API Key 进行认证，创建并返回一个新会话（session）。可选传入 `agent_role` 指定默认 Agent。后续 `/chat`、`/chat/stream`、`/logout` 都需要携带返回的 `session_id`。

**请求体 (JSON)：**

| 字段      | 类型   | 必填 | 说明            |
| --------- | ------ | ---- | --------------- |
| `api_key` | string | 是   | 前端 API Key |
| `agent_role` | string | 否 | 本会话默认 Agent 角色；不传则使用服务默认角色 |

**请求示例：**

```bash
curl -X POST http://localhost:8080/auth \
  -H "Content-Type: application/json" \
  -d '{"api_key": "sk-frontend-001", "agent_role": "internal-assistant"}'
```

**成功响应 200：**

```json
{
  "session_id": "a1b2c3d4-e5f6-...",
  "user_id": "user_001",
  "expires_at": "2026-05-22T15:30:00",
  "agent_role": "internal-assistant",
  "available_agent_roles": ["Webassistance", "internal-assistant"]
}
```

| 字段         | 类型   | 说明                              |
| ------------ | ------ | --------------------------------- |
| `session_id` | string | 会话唯一标识，后续请求都要携带      |
| `user_id`    | string | 用户标识                          |
| `expires_at` | string | 会话过期时间（ISO 8601 格式）      |
| `agent_role` | string | 本会话默认 Agent 角色 |
| `available_agent_roles` | array | 当前服务允许选择的 Agent 角色 |

**错误响应 401：**

```json
{ "detail": "Invalid API Key" }
```

---

## 4. 同步对话

```
POST /chat
```

**用途：** 发送消息给 Agent，等待完整回复后一次性返回。适合不需要流式展示的场景。

**请求体 (JSON)：**

| 字段         | 类型   | 必填 | 说明              |
| ------------ | ------ | ---- | ----------------- |
| `session_id` | string | 是   | 由 `/auth` 获取    |
| `message`    | string | 是   | 用户发送的消息内容 |
| `agent_role` | string | 否   | 指定本次对话使用哪个 Agent；不传则使用会话默认 Agent |

**请求示例：**

```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "a1b2c3d4-...", "agent_role": "internal-assistant", "message": "查一下 H13 库存"}'
```

**成功响应 200：**

```json
{
  "session_id": "a1b2c3d4-...",
  "content": "当然！请问你需要什么功能的 Python 代码？...",
  "role": "assistant",
  "agent_role": "internal-assistant"
}
```

| 字段         | 类型   | 说明                       |
| ------------ | ------ | -------------------------- |
| `session_id` | string | 会话标识                    |
| `content`    | string | Agent 的回复文本           |
| `role`       | string | 固定为 `"assistant"`       |
| `agent_role` | string | 本次回复对应的 Agent 角色 |

**错误响应 404：**

```json
{ "detail": "Session not found or expired" }
```

---

## 5. 流式对话 (SSE)

```
POST /chat/stream
```

**用途：** 发送消息给 Agent，以 Server-Sent Events 方式实时推送 Agent 生成的文本。前端推荐使用此接口，用户体验更好。

**请求体 (JSON)：**

| 字段         | 类型   | 必填 | 说明              |
| ------------ | ------ | ---- | ----------------- |
| `session_id` | string | 是   | 由 `/auth` 获取    |
| `message`    | string | 是   | 用户发送的消息内容 |
| `agent_role` | string | 否   | 指定本次流式对话使用哪个 Agent；不传则使用会话默认 Agent |

**请求示例：**

```bash
curl -X POST http://localhost:8080/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"session_id": "a1b2c3d4-...", "agent_role": "Webassistance", "message": "你好"}' \
  --no-buffer
```

**SSE 响应格式：**

```
data: "你好！"

data: "你好！有什么可以帮你的？"

data: "你好！有什么可以帮你的？请告诉我你的需求。"

data: [DONE]
```

每条 `data:` 行是一个 **JSON 编码的字符串**，包含截至当前时刻 Agent 生成的**完整文本**（累积更新，非增量）。最后以 `data: [DONE]` 结束。

> JSON 编码保证了文本中的换行符不会破坏 SSE 行格式。前端使用 `JSON.parse()` 即可还原原始文本。

**错误响应 404：**

```json
{ "detail": "Session not found or expired" }
```

### 前端消费示例（TypeScript）

```typescript
export async function* streamChat(
  sessionId: string,
  message: string,
  agentRole?: string,
): AsyncGenerator<string> {
  const res = await fetch(`${API_BASE}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, message, agent_role: agentRole }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Chat failed' }));
    throw new Error(err.detail || `Chat failed: ${res.status}`);
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error('No response body');

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6).trim();
        if (data === '[DONE]') return;
        if (data) yield JSON.parse(data);
      }
    }
  }
}
```

每次 `yield` 出来的是**完整累积文本**，直接替换 UI 中 assistant 消息的内容即可。

---

## 6. 登出 / 销毁会话

```
POST /logout
```

**用途：** 主动销毁指定会话，释放 Agent 资源。

**请求体 (JSON)：**

| 字段         | 类型   | 必填 | 说明              |
| ------------ | ------ | ---- | ----------------- |
| `session_id` | string | 是   | 由 `/auth` 获取    |

**请求示例：**

```bash
curl -X POST http://localhost:8080/logout \
  -H "Content-Type: application/json" \
  -d '{"session_id": "a1b2c3d4-..."}'
```

**成功响应 200：**

```json
{ "status": "logged out" }
```

---

## 通用错误码

| HTTP 状态码 | 含义                         |
| ----------- | ---------------------------- |
| 200         | 请求成功                     |
| 401         | API Key 无效（`/auth`）       |
| 404         | Session 不存在或已过期       |
| 422         | 请求体字段格式错误           |

## 会话生命周期

1. **创建：** 前端调用 `/auth`，传入 API Key，获得 `session_id`
2. **使用：** 同一 `session_id` 可多次调用 `/chat` 或 `/chat/stream`，Agent 会保持上下文记忆
3. **过期：** 会话空闲超过 **24 小时**后自动过期（由服务端定时清理）
4. **销毁：** 前端调用 `/logout` 主动销毁，或过期自动清理
