const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8080';
export const DEFAULT_API_KEY = import.meta.env.VITE_API_KEY || 'sk-frontend-001';

export interface AgentsInfo {
  default_agent_role: string;
  enabled_agent_roles: string[];
  available_agent_roles: string[];
}

export interface SessionInfo {
  session_id: string;
  user_id: string;
  expires_at: string;
  agent_role: string;
  available_agent_roles: string[];
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
}

export interface Session {
  id: string;
  userId: string;
  apiKey?: string;
  agentRole?: string;
  title: string;
  messages: ChatMessage[];
  createdAt: number;
}

/** GET /agents - 获取可用智能体 */
export async function getAgents(): Promise<AgentsInfo> {
  const res = await fetch(`${API_BASE}/agents`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to load agents' }));
    throw new Error(err.detail || `Failed to load agents: ${res.status}`);
  }
  return res.json();
}

/** POST /auth - 认证获取 session */
export async function auth(apiKey: string, agentRole?: string): Promise<SessionInfo> {
  const res = await fetch(`${API_BASE}/auth`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ api_key: apiKey, agent_role: agentRole }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Auth failed' }));
    throw new Error(err.detail || `Auth failed: ${res.status}`);
  }
  return res.json();
}

/** SSE 返回的结构化消息 */
export type StreamMessage =
  | { type: 'text'; msg_id?: string; content: string }
  | { type: 'action'; action: string; payload: Record<string, unknown> };

/** POST /chat/stream - 流式对话 */
export async function* streamChat(
  sessionId: string,
  message: string,
  agentRole?: string,
): AsyncGenerator<StreamMessage> {
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
        if (data) {
          const parsed = JSON.parse(data);
          // 兼容旧格式 (纯文本字符串)
          if (typeof parsed === 'string') {
            yield { type: 'text', content: parsed };
          } else {
            yield parsed as StreamMessage;
          }
        }
      }
    }
  }
}

/** POST /logout - 登出销毁会话 */
export async function logout(sessionId: string): Promise<void> {
  await fetch(`${API_BASE}/logout`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId }),
  });
}
