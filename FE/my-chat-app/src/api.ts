const API_BASE = 'http://localhost:8080';

export interface SessionInfo {
  session_id: string;
  user_id: string;
  expires_at: string;
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
  apiKey: string;
  title: string;
  messages: ChatMessage[];
  createdAt: number;
}

/** POST /auth - 认证获取 session */
export async function auth(apiKey: string): Promise<SessionInfo> {
  const res = await fetch(`${API_BASE}/auth`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ api_key: apiKey }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Auth failed' }));
    throw new Error(err.detail || `Auth failed: ${res.status}`);
  }
  return res.json();
}

/** POST /chat/stream - 流式对话 */
export async function* streamChat(
  sessionId: string,
  message: string,
): AsyncGenerator<string> {
  const res = await fetch(`${API_BASE}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, message }),
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
        if (data) yield data;
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
