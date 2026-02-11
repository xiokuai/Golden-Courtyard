# 架构设计说明

## 整体架构

```
┌──────────────┐     HTTP/REST      ┌─────────────────┐
│              │ ──────────────────► │  Django Views    │
│   浏览器      │                     │  (DRF ViewSets)  │
│  (单页应用)   │     WebSocket       ├─────────────────┤
│              │ ──────────────────► │  Channels        │
└──────────────┘                     │  (Consumers)     │
                                     ├─────────────────┤
                                     │  Daphne (ASGI)   │
                                     ├─────────────────┤
                                     │  SQLite          │
                                     └─────────────────┘
```

项目采用前后端一体的单页应用架构：

- 前端是一个纯 HTML/CSS/JS 文件（`templates/index.html`），由 Django 模板直接渲染
- 后端同时提供 REST API（数据 CRUD）和 WebSocket（实时通信）
- Daphne 作为 ASGI 服务器，同时处理 HTTP 和 WebSocket 请求

---

## 数据模型

```
User (AbstractUser)
 ├── avatar: URLField
 └── online: BooleanField

Server
 ├── name
 ├── owner → User
 ├── invite_code (唯一, 自动生成)
 └── created_at

Channel
 ├── name
 ├── server → Server
 ├── channel_type (text/voice)
 └── created_at

Membership
 ├── user → User
 ├── server → Server
 ├── role (owner/admin/member)
 └── joined_at
 └── unique_together: (user, server)

Message
 ├── content
 ├── author → User
 ├── channel → Channel
 ├── created_at
 └── updated_at

DirectMessage
 ├── content
 ├── sender → User
 ├── receiver → User
 ├── created_at
 └── is_read
```

---

## WebSocket 架构

项目使用 Django Channels 的 `InMemoryChannelLayer`，通过 group 机制广播消息：

**频道聊天（ChatConsumer）**

- 每个频道对应一个 group：`chat_{channel_id}`
- 每个服务器对应一个 group：`server_{server_id}`（用于在线状态广播）
- 连接时验证用户身份和服务器成员资格
- 断开时更新内存在线列表并同步数据库 `User.online` 字段

**私信（DmConsumer）**

- 每个用户对应一个 group：`dm_{user_id}`
- 用户登录后即建立连接，全局接收私信
- 发送私信时同时推送到发送者和接收者的 group

---

## 权限模型

| 操作 | 要求 |
|------|------|
| 创建服务器 | 已登录 |
| 修改/删除服务器 | owner |
| 创建频道 | 服务器成员 |
| 删除频道 | owner 或 admin |
| 发送消息 | 服务器成员 |
| 删除消息 | 消息作者 |
| 编辑消息 | 消息作者（仅 WebSocket） |

---

## 已知限制

- `InMemoryChannelLayer` 仅支持单进程，生产环境需替换为 Redis Channel Layer
- 语音频道（voice）模型已定义但未实现
- 用户头像字段存在但无上传接口
- 前端为单文件 SPA，未使用前端框架
