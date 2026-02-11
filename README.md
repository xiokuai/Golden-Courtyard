# Golden Courtyard

基于 Django + Channels 的实时聊天应用，类似 Discord 的服务器/频道/私信体验。

## 功能

- 用户注册/登录
- 创建服务器，通过邀请码加入
- 服务器内创建文字频道
- WebSocket 实时消息收发、编辑、删除
- 输入状态指示器
- 成员在线状态追踪
- 私信（WebSocket 实时推送）
- 消息分页加载（滚动加载历史）
- 基于角色的权限控制（owner / admin / member）

## 技术栈

- Python / Django 4.2
- Django Channels（WebSocket）
- Django REST Framework
- Daphne（ASGI 服务器）
- SQLite（开发环境）
- 原生 HTML / CSS / JavaScript（单页前端）

## 快速开始

```bash
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
├── app/                # 主应用
│   ├── models.py       # 数据模型（User, Server, Channel, Message, DM）
│   ├── views.py        # REST API 视图
│   ├── consumers.py    # WebSocket 消费者（聊天 + 私信）
│   ├── serializers.py  # DRF 序列化器
│   ├── routing.py      # WebSocket 路由
│   └── urls.py         # API 路由
├── config/             # Django 项目配置
├── templates/
│   └── index.html      # 单页前端
├── manage.py
└── requirements.txt
```

## License

MIT
