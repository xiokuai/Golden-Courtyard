# REST API 参考

所有 API 端点前缀为 `/api`，需要登录认证（除注册和登录外）。

## 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/register/` | 注册新用户 |
| POST | `/api/login/` | 用户登录 |
| POST | `/api/logout/` | 用户登出 |
| GET | `/api/me/` | 获取当前用户信息 |
| POST | `/api/me/avatar/` | 上传用户头像 |
| POST | `/api/me/status/` | 更新状态消息 |

### POST /api/register/

```json
// 请求
{ "username": "alice", "password": "secret123" }

// 响应 201
{ "id": 1, "username": "alice", "avatar": "", "online": false, "status_text": "" }
```

### POST /api/login/

```json
// 请求
{ "username": "alice", "password": "secret123" }

// 响应 200
{ "id": 1, "username": "alice", "avatar": "", "online": false, "status_text": "" }

// 错误 401
{ "detail": "用户名或密码错误" }
```

### POST /api/me/avatar/

上传用户头像，使用 `multipart/form-data`，字段名 `avatar`，限制 2MB。

```json
// 响应 200
{ "id": 1, "username": "alice", "avatar": "http://host/media/avatars/xxx.jpg", "online": true, "status_text": "" }
```

### POST /api/me/status/

```json
// 请求
{ "status_text": "正在摸鱼" }

// 响应 200
{ "id": 1, "username": "alice", "avatar": "", "online": true, "status_text": "正在摸鱼" }
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
| POST | `/api/servers/:id/role/` | 修改成员角色（仅 owner） |
| POST | `/api/servers/:id/kick/` | 踢出成员（owner/admin） |
| POST | `/api/servers/:id/icon/` | 上传服务器图标（仅 owner） |

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

### POST /api/servers/:id/role/

```json
// 请求（role 可选 admin / member）
{ "user_id": 2, "role": "admin" }

// 响应 200
{ "detail": "已设为管理员" }
```

### POST /api/servers/:id/kick/

```json
// 请求
{ "user_id": 2 }

// 响应 200
{ "detail": "已踢出该成员" }
```

### POST /api/servers/:id/icon/

上传服务器图标，使用 `multipart/form-data`，字段名 `icon`，限制 2MB，仅 owner 可操作。

```json
// 响应 200
{ "id": 1, "name": "我的服务器", "icon": "http://host/media/server_icons/xxx.jpg", ... }
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

### 发送消息

```json
// 请求（reply_to_id 可选，用于回复某条消息）
{ "content": "你好", "reply_to_id": 42 }

// 响应 201
{
  "id": 43, "content": "你好",
  "author": { "id": 1, "username": "alice", "avatar": "", "online": true, "status_text": "" },
  "reply_to": { "id": 42, "content": "原消息内容", "author": {...} },
  "created_at": "...", "updated_at": "..."
}
```

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

---

## 未读消息

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/unread/` | 获取所有频道未读消息数 |
| POST | `/api/channels/:channel_id/read/` | 标记频道已读 |

### GET /api/unread/

```json
// 响应 200 — key 为频道 ID，value 为未读数（仅返回 > 0 的）
{ "3": 5, "7": 12 }
```

### POST /api/channels/:channel_id/read/

```json
// 响应 200
{ "ok": true }
```

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
