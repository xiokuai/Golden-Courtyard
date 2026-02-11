import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Message, Channel, Membership, User, DirectMessage

# 在内存中追踪在线用户 {server_id: {user_id, ...}}
online_users = {}


class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.channel_id = self.scope['url_route']['kwargs']['channel_id']
        self.room_group = f'chat_{self.channel_id}'
        self.user = self.scope['user']
        self.server_id = None

        if self.user.is_anonymous:
            await self.close()
            return

        self.server_id = await self.get_server_id()
        if not self.server_id:
            await self.close()
            return

        self.server_group = f'server_{self.server_id}'

        await self.channel_layer.group_add(self.room_group, self.channel_name)
        await self.channel_layer.group_add(self.server_group, self.channel_name)
        await self.accept()

        # 标记上线
        if self.server_id not in online_users:
            online_users[self.server_id] = set()
        online_users[self.server_id].add(self.user.id)
        await self.set_user_online(True)

        await self.channel_layer.group_send(self.server_group, {
            'type': 'presence_update',
            'user_id': self.user.id,
            'username': self.user.username,
            'status': 'online',
        })

    async def disconnect(self, code):
        if self.server_id:
            await self.channel_layer.group_discard(self.room_group, self.channel_name)
            await self.channel_layer.group_discard(self.server_group, self.channel_name)

            if self.server_id in online_users:
                online_users[self.server_id].discard(self.user.id)

            # 检查用户是否在其他服务器还有连接
            still_online = any(self.user.id in ids for ids in online_users.values())
            if not still_online:
                await self.set_user_online(False)

            await self.channel_layer.group_send(self.server_group, {
                'type': 'presence_update',
                'user_id': self.user.id,
                'username': self.user.username,
                'status': 'offline',
            })

    async def receive_json(self, content):
        msg_type = content.get('type', 'message')

        if msg_type == 'message':
            text = content.get('content', '').strip()
            if not text:
                return
            reply_to_id = content.get('reply_to')
            message = await self.save_message(text, reply_to_id)
            await self.channel_layer.group_send(self.room_group, {
                'type': 'chat_message',
                'message': message,
            })

        elif msg_type == 'typing':
            await self.channel_layer.group_send(self.room_group, {
                'type': 'typing_indicator',
                'user_id': self.user.id,
                'username': self.user.username,
            })

        elif msg_type == 'edit_message':
            msg_id = content.get('message_id')
            new_content = content.get('content', '').strip()
            if not msg_id or not new_content:
                return
            result = await self.edit_message(msg_id, new_content)
            if result:
                await self.channel_layer.group_send(self.room_group, {
                    'type': 'message_edited',
                    'message': result,
                })

        elif msg_type == 'delete_message':
            msg_id = content.get('message_id')
            if not msg_id:
                return
            ok = await self.delete_message(msg_id)
            if ok:
                await self.channel_layer.group_send(self.room_group, {
                    'type': 'message_deleted',
                    'message_id': msg_id,
                })

    # ---- 事件处理器 ----
    async def chat_message(self, event):
        await self.send_json({'type': 'message', **event['message']})

    async def typing_indicator(self, event):
        if event['user_id'] != self.user.id:
            await self.send_json({
                'type': 'typing',
                'user_id': event['user_id'],
                'username': event['username'],
            })

    async def message_edited(self, event):
        await self.send_json({'type': 'edit', **event['message']})

    async def message_deleted(self, event):
        await self.send_json({'type': 'delete', 'message_id': event['message_id']})

    async def presence_update(self, event):
        await self.send_json({
            'type': 'presence',
            'user_id': event['user_id'],
            'username': event['username'],
            'status': event['status'],
        })

    # ---- 数据库操作 ----
    @database_sync_to_async
    def set_user_online(self, is_online):
        User.objects.filter(pk=self.user.id).update(online=is_online)

    @database_sync_to_async
    def get_server_id(self):
        try:
            ch = Channel.objects.select_related('server').get(pk=self.channel_id)
            if Membership.objects.filter(user=self.user, server=ch.server).exists():
                return ch.server_id
        except Channel.DoesNotExist:
            pass
        return None

    @database_sync_to_async
    def save_message(self, text, reply_to_id=None):
        kwargs = dict(content=text, author=self.user, channel_id=self.channel_id)
        if reply_to_id:
            try:
                reply_msg = Message.objects.select_related('author').get(pk=reply_to_id)
                kwargs['reply_to'] = reply_msg
            except Message.DoesNotExist:
                pass
        msg = Message.objects.create(**kwargs)
        result = {
            'id': msg.id,
            'content': msg.content,
            'author': {
                'id': self.user.id,
                'username': self.user.username,
                'avatar': self.user.avatar,
            },
            'channel': msg.channel_id,
            'created_at': msg.created_at.isoformat(),
            'reply_to': None,
        }
        if msg.reply_to_id:
            rt = msg.reply_to if hasattr(msg, '_reply_to_cache') else Message.objects.select_related('author').filter(pk=msg.reply_to_id).first()
            if not rt:
                rt = reply_msg
            result['reply_to'] = {
                'id': rt.id,
                'content': rt.content,
                'author': {'id': rt.author.id, 'username': rt.author.username},
            }
        return result

    @database_sync_to_async
    def edit_message(self, msg_id, new_content):
        try:
            msg = Message.objects.get(pk=msg_id, author=self.user)
            msg.content = new_content
            msg.save()
            return {
                'id': msg.id,
                'content': msg.content,
                'updated_at': msg.updated_at.isoformat(),
            }
        except Message.DoesNotExist:
            return None

    @database_sync_to_async
    def delete_message(self, msg_id):
        try:
            msg = Message.objects.get(pk=msg_id, author=self.user)
            msg.delete()
            return True
        except Message.DoesNotExist:
            return False


class DmConsumer(AsyncJsonWebsocketConsumer):
    """私信 WebSocket，每个用户连接到自己的 dm_{user_id} 组"""

    async def connect(self):
        self.user = self.scope['user']
        if self.user.is_anonymous:
            await self.close()
            return
        self.group_name = f'dm_{self.user.id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content):
        msg_type = content.get('type', 'message')
        if msg_type == 'message':
            receiver_id = content.get('receiver_id')
            text = content.get('content', '').strip()
            if not receiver_id or not text:
                return
            result = await self.save_dm(receiver_id, text)
            if not result:
                return
            # 发送给接收者
            await self.channel_layer.group_send(f'dm_{receiver_id}', {
                'type': 'dm_message',
                'message': result,
            })
            # 也发送给自己
            await self.channel_layer.group_send(self.group_name, {
                'type': 'dm_message',
                'message': result,
            })

    async def dm_message(self, event):
        await self.send_json({'type': 'dm', **event['message']})

    @database_sync_to_async
    def save_dm(self, receiver_id, text):
        try:
            receiver = User.objects.get(pk=receiver_id)
        except User.DoesNotExist:
            return None
        dm = DirectMessage.objects.create(
            sender=self.user, receiver=receiver, content=text,
        )
        return {
            'id': dm.id,
            'content': dm.content,
            'sender': {'id': self.user.id, 'username': self.user.username},
            'receiver': {'id': receiver.id, 'username': receiver.username},
            'created_at': dm.created_at.isoformat(),
        }
