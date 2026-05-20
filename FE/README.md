# AgentScope Chat — 前端

基于 React + TypeScript + Vite 构建的 DeepSeek 风格聊天应用，与 AgentScope Agent 后端配合使用。

## 快速开始

```bash
cd my-chat-app

# 安装依赖
npm install

# 启动开发服务器（默认 http://localhost:5173）
npm run dev

# 生产构建
npm run build
```

## 技术栈

| 技术         | 说明             |
| ------------ | ---------------- |
| React 19     | UI 框架          |
| TypeScript   | 类型安全         |
| Vite         | 构建工具         |
| CSS (无框架) | 纯 CSS 手写样式  |

## 项目结构

```text
FE/my-chat-app/
├── index.html              # 入口 HTML
├── package.json
├── vite.config.ts
├── tsconfig.json
└── src/
    ├── main.tsx            # React 挂载入口
    ├── api.ts              # 后端 API 封装（auth / 流式聊天 / logout）
    ├── App.tsx             # 应用主体（侧边栏 + 聊天区 + 认证弹窗）
    ├── App.css             # 全局样式
    └── index.css           # CSS 重置 + 滚动条美化
```

## 功能说明

### 会话管理

- **新建会话**：点击侧边栏 "+" 按钮 → 选择 API Key 认证 → 调用 `/auth` 获取 `session_id` → 创建新会话
- **切换会话**：点击左侧会话列表中的任意会话即可切换，消息历史从 localStorage 恢复
- **删除会话**：悬停会话项 → 点击删除图标 → 确认 → 调用 `/logout` 销毁后端会话
- **持久化**：所有会话和消息存储在 localStorage，刷新不丢失

### 聊天功能

- **流式响应**：默认使用 `/chat/stream` 端点，SSE (Server-Sent Events) 逐字渲染 AI 回复
- **自动命名**：发送第一条消息后，取前 30 个字符自动作为会话标题
- **快捷提示**：空会话时展示提示卡片，点击即可开始对话
- **Enter 发送**：Enter 键发送消息，Shift+Enter 换行

### UI 特性

- 左侧深色侧边栏（可折叠），右侧白色聊天区
- 用户消息蓝色气泡靠右，AI 消息灰色气泡靠左，带头像
- 响应式布局：移动端侧边栏覆盖显示
- 输入框聚焦高亮、发送按钮旋转动画

## 后端依赖

前端默认连接 `http://localhost:8080`，需要以下端点：

| 方法 | 路径             | 说明                             |
| ---- | ---------------- | -------------------------------- |
| POST | `/auth`          | API Key 认证，返回 `session_id`  |
| POST | `/chat/stream`   | SSE 流式对话                     |
| POST | `/logout`        | 销毁会话                         |

在 [src/api.ts](my-chat-app/src/api.ts) 中修改 `API_BASE` 可更改后端地址。

## 预设 API Key

| Key                | 用户     |
| ------------------ | -------- |
| `sk-frontend-001`  | user_001 |
| `sk-frontend-002`  | user_002 |
