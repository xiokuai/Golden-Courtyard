# REST API 参考

所有 API 端点前缀为 `/api`，需要登录认证（除注册和登录外）。

## 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/register/` | 注册新用户 |
| POST | `/api/login/` | 用户登录 |
| POST | `/api/logout/` | 用户登出 |
| GET | `/api/me/` | 获取当前用户信息 |

### POST /api/register/

```json
// 请求
{ "username": "alice", "password": "secret123" }

// 响应 201
{ "id": 1, "username": "alice", "avatar": "", "online": false }
```

### POST /api/login/

```json
// 请求
{ "username": "alice", "password": "secret123" }

// 响应 200
{ "id": 1, "username": "alice", "avatar": "", "online": false }

// 错误 401
{ "detail": "用户名或密码错误" }
```

---

## 服务器

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/servers/` | 获取已加入的服务器列表 |
| POST | `/api/servers/` | 创建服务器 |
| GET | `/api/servers/:id/` | 获取服务器详情 |
| PUT | `/api/servers/:id/` | 更新服务器（仅 owner） |
| DELETE | `/api/servers/:id/` | 删除服务器（仅 owner） |
| POST | `/api/servers/join/` | 通过邀请码加入服务器 |
| POST | `/api/servers/:id/leave/` | 退出服务器 |
| GET | `/api/servers/:id/members/` | 获取服务器成员列表 |
| GET | `/api/servers/:id/online/` | 获取在线成员 ID 列表 |

### POST /api/servers/

```json
// 请求
{ "name": "我的服务器" }

// 响应 201 — 自动生成邀请码，创建默认频道"综合"
{ "id": 1, "name": "我的服务器", "invite_code": "a1b2c3d4", "owner": {...}, "channels": [...] }
```

### POST /api/servers/join/

```json
// 请求
{ "invite_code": "a1b2c3d4" }

// 响应 201
{ "id": 1, "name": "我的服务器", ... }

// 错误 404
{ "detail": "邀请码无效" }
```

---

## 频道

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/servers/:server_id/channels/` | 获取频道列表 |
| POST | `/api/servers/:server_id/channels/` | 创建频道（需为成员） |
| DELETE | `/api/servers/:server_id/channels/:id/` | 删除频道（需 owner/admin） |

### POST /api/servers/:server_id/channels/

```json
// 请求
{ "name": "公告" }

// 响应 201
{ "id": 2, "name": "公告", "channel_type": "text", "server": 1 }
```

---

## 消息

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/channels/:channel_id/messages/` | 获取消息列表（分页） |
| POST | `/api/channels/:channel_id/messages/` | 发送消息 |
| DELETE | `/api/channels/:channel_id/messages/:id/` | 删除消息（仅作者） |

### 分页参数

- `before` — 消息 ID，返回该 ID 之前的 50 条消息（用于加载历史）

```
GET /api/channels/1/messages/?before=100
```

---

## 私信

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/dm/` | 获取私信会话列表（含未读数） |
| GET | `/api/dm/:user_id/` | 获取与某用户的私信记录（分页） |
| POST | `/api/dm/:user_id/` | 发送私信（REST 备用，推荐用 WebSocket） |
| GET | `/api/users/search/?q=xxx` | 搜索用户（最多 10 条） |

### GET /api/dm/

```json
// 响应 200
[
  {
    "user": { "id": 2, "username": "bob" },
    "last_message": "你好",
    "last_time": "2025-01-01T12:00:00",
    "unread": 3
  }
]
```
