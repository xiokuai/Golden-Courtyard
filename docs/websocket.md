# WebSocket 协议说明

项目使用两个 WebSocket 端点，分别处理频道消息和私信。

## 连接地址

| 端点 | 路径 | 说明 |
|------|------|------|
| 频道聊天 | `ws://<host>/ws/chat/<channel_id>/` | 加入指定频道的实时聊天 |
| 私信 | `ws://<host>/ws/dm/` | 接收和发送私信 |

连接需要已登录的 Session 认证，匿名用户会被拒绝连接。

---

## 频道聊天（ChatConsumer）

### 客户端发送

**发送消息**

```json
{ "type": "message", "content": "你好" }
```

**发送消息（带回复）**

```json
{ "type": "message", "content": "同意", "reply_to": 42 }
```

**发送输入状态**

```json
{ "type": "typing" }
```

**编辑消息**（仅自己的消息）

```json
{ "type": "edit_message", "message_id": 42, "content": "修改后的内容" }
```

**删除消息**（仅自己的消息）

```json
{ "type": "delete_message", "message_id": 42 }
```

### 服务端推送

**新消息**

```json
{
  "type": "message",
  "id": 43,
  "content": "你好",
  "author": { "id": 1, "username": "alice", "avatar": "" },
  "channel": 1,
  "reply_to": { "id": 42, "content": "原消息", "author": { "id": 2, "username": "bob" } },
  "created_at": "2025-01-01T12:00:00"
}
```

**输入状态**（不会推送给发送者自己）

```json
{ "type": "typing", "user_id": 2, "username": "bob" }
```

**消息已编辑**

```json
{ "type": "edit", "id": 42, "content": "修改后的内容", "updated_at": "..." }
```

**消息已删除**

```json
{ "type": "delete", "message_id": 42 }
```

**在线状态变更**

```json
{ "type": "presence", "user_id": 2, "username": "bob", "status": "online" }
```

---

## 私信（DmConsumer）

### 客户端发送

**发送私信**

```json
{ "type": "message", "receiver_id": 2, "content": "嗨" }
```

### 服务端推送

**收到私信**（发送者和接收者都会收到）

```json
{
  "type": "dm",
  "id": 10,
  "content": "嗨",
  "sender": { "id": 1, "username": "alice" },
  "receiver": { "id": 2, "username": "bob" },
  "created_at": "2025-01-01T12:00:00"
}
```

---

## 重连机制

前端对两个 WebSocket 连接都实现了指数退避重连：

- 初始延迟 1 秒，每次翻倍，最大 30 秒
- 连接成功后重置计数器
- 频道 WebSocket 在切换频道或退出时停止重连
- 私信 WebSocket 在用户登出时停止重连
