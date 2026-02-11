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
 ├── avatar: ImageField (upload_to='avatars/')
 ├── online: BooleanField
 └── status_text: CharField (max 100)

Server
 ├── name
 ├── icon: ImageField (upload_to='server_icons/')
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
 ├── joined_at
 └── unique_together: (user, server)

Message
 ├── content
 ├── author → User
 ├── channel → Channel
 ├── reply_to → Message (可空, SET_NULL)
 ├── created_at
 └── updated_at

ChannelReadState
 ├── user → User
 ├── channel → Channel
 ├── last_read_id: PositiveBigIntegerField
 └── unique_together: (user, channel)

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
| 上传服务器图标 | owner |
| 创建频道 | 服务器成员 |
| 删除频道 | owner 或 admin |
| 修改成员角色 | owner |
| 踢出成员 | owner 或 admin（admin 不能踢 admin） |
| 发送消息 | 服务器成员 |
| 删除消息 | 消息作者 |
| 编辑消息 | 消息作者（仅 WebSocket） |
| 上传头像 | 已登录（限 2MB） |
| 更新状态 | 已登录 |

---

## 已知限制

- `InMemoryChannelLayer` 仅支持单进程，生产环境需替换为 Redis Channel Layer
- 语音频道（voice）模型已定义但未实现
- 前端为单文件 SPA，未使用前端框架
- 文件上传存储在本地 `media/` 目录，生产环境建议使用对象存储
- 主题设置仅保存在浏览器 localStorage，不同设备不同步
