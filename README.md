# Golden Courtyard

基于 Django + Channels 的实时聊天应用，提供类似 Discord 的服务器、频道、私信体验。

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Django](https://img.shields.io/badge/Django-4.2-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## 功能特性

**服务器与频道**
- 创建/删除服务器，自动生成 8 位邀请码
- 通过邀请码加入服务器
- 服务器内创建多个文字频道
- 基于角色的权限控制（owner / admin / member）
- 角色管理：设置管理员、踢出成员
- 服务器图标上传

**实时消息**
- WebSocket 实时收发消息
- 消息编辑与删除
- 消息回复（引用）
- Markdown 渲染（代码块、加粗、斜体、链接等）
- 输入状态指示器（正在输入...）
- 滚动加载历史消息（每次 50 条分页）
- 频道未读消息追踪与角标
- 断线自动重连（指数退避）

**私信系统**
- 用户搜索，发起私信对话
- WebSocket 实时私信推送
- 未读消息计数
- 右键成员面板快速发起私信

**个性化**
- 用户头像上传（限 2MB）
- 自定义状态消息
- 深色/浅色主题切换
- 6 种主题色可选，设置持久化
- 用户资料卡片（点击成员查看）

**Bot 功能**
- B站视频解析：发送 BV/AV号或 bilibili 链接，自动解析视频信息
- 随机图片：发送 `/img` 获取随机图片
- 快捷换头像：发送 `/myimg <图片URL>` 快速更换头像
- AI 对话：在系统服务器或私信中与 Bot 聊天，基于 DeepSeek API
- 人设切换：管理员使用 `/name <人设名>` 切换 Bot 人设（默认 Elysia）

**在线状态**
- 实时在线/离线状态追踪
- 成员面板分组显示在线与离线用户
- 状态同步写入数据库

**移动端适配**
- 响应式布局（≤768px）
- 侧栏折叠与汉堡菜单

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | Django 4.2 |
| WebSocket | Django Channels + Daphne |
| REST API | Django REST Framework |
| 数据库 | SQLite（开发）|
| 前端 | 原生 HTML / CSS / JavaScript |
| 认证 | Django Session Auth |

## 快速开始

```bash
# 克隆项目
git clone https://github.com/xiokuai/Golden-Courtyard.git
cd Golden-Courtyard

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt

# 初始化数据库
python manage.py migrate

# 创建管理员（可选）
python manage.py createsuperuser

# 启动服务
python manage.py runserver
```

浏览器打开 `http://127.0.0.1:8000` 即可使用。

## 项目结构

```
Golden-Courtyard/
├── app/                  # 主应用
│   ├── models.py         # 数据模型（User, Server, Channel, Message, DM 等）
│   ├── views.py          # REST API 视图 + 权限控制
│   ├── consumers.py      # WebSocket 消费者（ChatConsumer + DmConsumer）
│   ├── bilibili.py       # B站视频解析 + 随机图片 + 头像下载
│   ├── deepseek.py       # DeepSeek AI 对话 + 人设管理
│   ├── serializers.py    # DRF 序列化器
│   ├── routing.py        # WebSocket 路由
│   ├── urls.py           # API 路由
│   ├── admin.py          # Django Admin 注册
│   └── migrations/       # 数据库迁移文件
├── config/               # Django 项目配置
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── templates/
│   └── index.html        # 单页前端（HTML + CSS + JS）
├── media/                # 用户上传文件（头像、图标）
├── docs/                 # 开发者文档
│   ├── api.md            # REST API 参考
│   ├── websocket.md      # WebSocket 协议说明
│   ├── architecture.md   # 架构设计说明
│   └── help.md           # 使用帮助
├── manage.py
├── requirements.txt
└── README.md
```

## 文档

详细的开发者文档位于 [docs/](./docs/) 目录：

- [API 参考](./docs/api.md) — REST API 端点说明
- [WebSocket 协议](./docs/websocket.md) — WebSocket 消息格式与事件
- [架构设计](./docs/architecture.md) — 项目架构与数据模型
- [使用帮助](./docs/help.md) — 功能使用指南

## License

MIT
