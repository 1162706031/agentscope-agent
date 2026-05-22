import { useState, useRef, useEffect, useCallback } from 'react';
import type { Session, ChatMessage, StreamMessage } from './api';
import { auth, streamChat, logout as apiLogout } from './api';
import './App.css';

const API_KEYS = ['sk-frontend-001', 'sk-frontend-002'];

/* ─── localStorage helpers ─── */
function loadSessions(): Session[] {
  try {
    const raw = localStorage.getItem('chat_sessions');
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveSessions(sessions: Session[]) {
  localStorage.setItem('chat_sessions', JSON.stringify(sessions));
}

/* ─── App ─── */
export default function App() {
  const [sessions, setSessions] = useState<Session[]>(loadSessions);
  const [activeId, setActiveId] = useState<string | null>(
    () => loadSessions()[0]?.id ?? null,
  );
  const [showAuth, setShowAuth] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const activeSession = sessions.find((s) => s.id === activeId) ?? null;

  const persist = useCallback((next: Session[]) => {
    setSessions(next);
    saveSessions(next);
  }, []);

  /* 新建 session —— 先弹窗认证再创建 */
  const handleNewSession = async (apiKey: string) => {
    try {
      const info = await auth(apiKey);
      const session: Session = {
        id: info.session_id,
        userId: info.user_id,
        apiKey,
        title: '新对话',
        messages: [],
        createdAt: Date.now(),
      };
      const next = [session, ...sessions];
      persist(next);
      setActiveId(session.id);
      setShowAuth(false);
    } catch (e: any) {
      alert('认证失败: ' + e.message);
    }
  };

  /* 切换 session */
  const handleSelect = (id: string) => setActiveId(id);

  /* 删除 session */
  const handleDelete = async (id: string) => {
    try {
      await apiLogout(id);
    } catch {
      // 即使后端失败也删掉前端记录
    }
    const next = sessions.filter((s) => s.id !== id);
    persist(next);
    if (activeId === id) {
      setActiveId(next[0]?.id ?? null);
    }
  };

  /* 发送消息 */
  const handleSend = async (text: string) => {
    if (!activeSession) {
      setShowAuth(true);
      return;
    }

    const userMsg: ChatMessage = {
      id: `u-${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: Date.now(),
    };

    // 首次消息自动命名
    const isFirst = activeSession.messages.length === 0;
    const seed: Session = {
      ...activeSession,
      title: isFirst ? (text.slice(0, 30) + (text.length > 30 ? '...' : '')) : activeSession.title,
      messages: [...activeSession.messages, userMsg],
    };
    persist(sessions.map((s) => (s.id === seed.id ? seed : s)));
    setActiveId(seed.id);

    // backend msg_id → 前端 bubble id 映射
    const bubbleMap = new Map<string, string>();
    let seq = 0;

    try {
      for await (const chunk of streamChat(activeSession.id, text)) {
        seq++;
        console.log(`[Chat] chunk ${seq}:`, chunk);

        if (chunk.type === 'text') {
          const backendId = chunk.msg_id || `_fallback_${seq}`;

          const bubbleId = bubbleMap.get(backendId);
          if (!bubbleId) {
            // 新 backend 消息 → 创建新 bubble
            const newId = `a-${Date.now()}-${seq}`;
            bubbleMap.set(backendId, newId);
            const newBubble: ChatMessage = {
              id: newId,
              role: 'assistant',
              content: chunk.content,
              timestamp: Date.now(),
            };
            setSessions((prev) =>
              prev.map((s) => {
                if (s.id !== activeSession.id) return s;
                return { ...s, messages: [...s.messages, newBubble] };
              }),
            );
          } else {
            // 同一个 backend 消息在流式输出 → 更新对应 bubble
            setSessions((prev) =>
              prev.map((s) => {
                if (s.id !== activeSession.id) return s;
                return {
                  ...s,
                  messages: s.messages.map((m) =>
                    m.id === bubbleId ? { ...m, content: chunk.content } : m,
                  ),
                };
              }),
            );
          }
        } else if (chunk.type === 'action') {
          console.log('[Chat] action:', chunk.action, chunk.payload);
          if (chunk.action === 'page_navigation') {
            const { url } = chunk.payload as { url: string; content: string };
            console.log('[Chat] 页面导航:', url);
          }
        }
      }

      console.log('[Chat] 流式完成');
    } catch (e: any) {
      console.error('[Chat] 流式错误:', e);
      // 最后一个 bubble 显示错误
      const lastBubbleId = [...bubbleMap.values()].pop();
      setSessions((prev) => {
        const next = prev.map((s) => {
          if (s.id !== activeSession.id) return s;
          return {
            ...s,
            messages: s.messages.map((m) =>
              lastBubbleId && m.id === lastBubbleId
                ? { ...m, content: `错误: ${e.message}` }
                : m,
            ),
          };
        });
        saveSessions(next);
        return next;
      });
      return;
    }
    // 流式完成后持久化最终结果
    setSessions((prev) => {
      saveSessions(prev);
      return prev;
    });
  };

  return (
    <div className="app-shell">
      {/* 侧边栏 */}
      <Sidebar
        sessions={sessions}
        activeId={activeId}
        onSelect={handleSelect}
        onDelete={handleDelete}
        onNew={() => setShowAuth(true)}
        open={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
      />

      {/* 主聊天区域 */}
      <ChatArea
        session={activeSession}
        onSend={handleSend}
        onNewChat={() => setShowAuth(true)}
        sidebarOpen={sidebarOpen}
        onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
      />

      {/* 认证弹窗 */}
      {showAuth && (
        <AuthModal
          onConfirm={handleNewSession}
          onClose={() => setShowAuth(false)}
        />
      )}
    </div>
  );
}

/* ─── Sidebar ─── */
function Sidebar({
  sessions,
  activeId,
  onSelect,
  onDelete,
  onNew,
  open,
  onToggle,
}: {
  sessions: Session[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
  onNew: () => void;
  open: boolean;
  onToggle: () => void;
}) {
  return (
    <aside className={`sidebar ${open ? 'open' : 'closed'}`}>
      <div className="sidebar-header">
        <button className="icon-btn sidebar-toggle" onClick={onToggle}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
            <line x1="9" y1="3" x2="9" y2="21" />
          </svg>
        </button>
        {open && <span className="sidebar-title">对话列表</span>}
        {open && (
          <button className="icon-btn new-chat-btn" onClick={onNew} title="新建对话">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
            </svg>
          </button>
        )}
      </div>

      {open && (
        <div className="session-list">
          {sessions.length === 0 && (
            <div className="session-empty">暂无对话，点击 + 开始</div>
          )}
          {sessions.map((s) => (
            <div
              key={s.id}
              className={`session-item ${s.id === activeId ? 'active' : ''}`}
              onClick={() => onSelect(s.id)}
            >
              <span className="session-title" title={s.title}>
                {s.title}
              </span>
              <button
                className="icon-btn session-delete"
                onClick={(e) => {
                  e.stopPropagation();
                  if (confirm('确定删除该对话？')) onDelete(s.id);
                }}
                title="删除"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="3 6 5 6 21 6" />
                  <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                  <path d="M10 11v6" /><path d="M14 11v6" />
                </svg>
              </button>
            </div>
          ))}
        </div>
      )}
    </aside>
  );
}

/* ─── ChatArea ─── */
function ChatArea({
  session,
  onSend,
  onNewChat,
  sidebarOpen,
  onToggleSidebar,
}: {
  session: Session | null;
  onSend: (text: string) => Promise<void>;
  onNewChat: () => void;
  sidebarOpen: boolean;
  onToggleSidebar: () => void;
}) {
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [session?.messages]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || sending) return;
    setInput('');
    setSending(true);
    try {
      await onSend(text);
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // 自动调高 textarea
  const adjustHeight = () => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = 'auto';
      el.style.height = Math.min(el.scrollHeight, 200) + 'px';
    }
  };

  return (
    <main className="chat-main">
      {/* 顶部栏 */}
      <header className="chat-topbar">
        <div className="topbar-left">
          {!sidebarOpen && (
            <button className="icon-btn" onClick={onToggleSidebar}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                <line x1="9" y1="3" x2="9" y2="21" />
              </svg>
            </button>
          )}
          <h1 className="topbar-title">
            {session?.title ?? 'DeepSeek Chat'}
          </h1>
        </div>
      </header>

      {/* 消息区 */}
      <div className="messages-area">
        {(!session || session.messages.length === 0) ? (
          <div className="welcome-screen">
            <div className="welcome-logo">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
            </div>
            <h2 className="welcome-title">有什么可以帮你的？</h2>
            <div className="welcome-hints">
              {['帮我写一段 Python 代码', '解释一下什么是机器学习', '帮我翻译一段英文', '今天有什么新闻'].map((hint) => (
                <button
                  key={hint}
                  className="hint-chip"
                  onClick={() => {
                    if (!session) {
                      onNewChat();
                      // 需要在认证完成后发送，这里先触发 new chat
                      setTimeout(() => {
                        setInput(hint);
                      }, 500);
                    } else {
                      onSend(hint);
                    }
                  }}
                >
                  {hint}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="message-list">
            {session.messages.map((m) => (
              <MessageBubble key={m.id} msg={m} />
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* 输入区 */}
      <div className="composer">
        <div className="composer-inner">
          <textarea
            ref={textareaRef}
            className="composer-textarea"
            rows={1}
            placeholder="输入消息，Enter 发送，Shift+Enter 换行"
            value={input}
            onChange={(e) => {
              setInput(e.target.value);
              adjustHeight();
            }}
            onKeyDown={handleKeyDown}
            disabled={sending}
          />
          <button
            className="send-btn"
            onClick={handleSend}
            disabled={!input.trim() || sending}
          >
            {sending ? (
              <span className="spinner" />
            ) : (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
              </svg>
            )}
          </button>
        </div>
      </div>
    </main>
  );
}

/* ─── Message Bubble ─── */
function MessageBubble({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === 'user';
  return (
    <div className={`msg-row ${isUser ? 'user-msg' : 'assistant-msg'}`}>
      {!isUser && (
        <div className="msg-avatar assistant-avatar-icon">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
        </div>
      )}
      <div className={`msg-bubble ${isUser ? 'bubble-user' : 'bubble-assistant'}`}>
        {isUser ? (
          msg.content
        ) : (
          msg.content || <span className="typing-cursor" />
        )}
      </div>
    </div>
  );
}

/* ─── Auth Modal ─── */
function AuthModal({
  onConfirm,
  onClose,
}: {
  onConfirm: (key: string) => void;
  onClose: () => void;
}) {
  const [selected, setSelected] = useState(API_KEYS[0]);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <h2 className="modal-title">API Key 认证</h2>
        <p className="modal-desc">选择 API Key 创建新会话</p>
        <div className="key-list">
          {API_KEYS.map((k) => (
            <label
              key={k}
              className={`key-option ${selected === k ? 'selected' : ''}`}
            >
              <input
                type="radio"
                name="apikey"
                value={k}
                checked={selected === k}
                onChange={() => setSelected(k)}
              />
              <span className="key-text">{k}</span>
            </label>
          ))}
        </div>
        <div className="modal-actions">
          <button className="btn-secondary" onClick={onClose}>取消</button>
          <button className="btn-primary" onClick={() => onConfirm(selected)}>
            确认并创建会话
          </button>
        </div>
      </div>
    </div>
  );
}
