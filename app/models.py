from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid


class User(AbstractUser):
    """自定义用户，扩展头像和在线状态"""
    avatar = models.URLField(blank=True, default='')
    online = models.BooleanField(default=False)

    class Meta:
        db_table = 'users'


class Server(models.Model):
    """服务器 (类似 Discord 的 Guild)"""
    name = models.CharField(max_length=100)
    icon = models.URLField(blank=True, default='')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_servers')
    invite_code = models.CharField(max_length=20, unique=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.invite_code:
            self.invite_code = uuid.uuid4().hex[:8]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'servers'


class Channel(models.Model):
    """频道 (文字频道)"""
    CHANNEL_TYPES = [
        ('text', '文字频道'),
        ('voice', '语音频道'),
    ]
    name = models.CharField(max_length=100)
    server = models.ForeignKey(Server, on_delete=models.CASCADE, related_name='channels')
    channel_type = models.CharField(max_length=10, choices=CHANNEL_TYPES, default='text')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'#{self.name}'

    class Meta:
        db_table = 'channels'


class Membership(models.Model):
    """服务器成员关系"""
    ROLE_CHOICES = [
        ('owner', '所有者'),
        ('admin', '管理员'),
        ('member', '成员'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='memberships')
    server = models.ForeignKey(Server, on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'memberships'
        unique_together = ('user', 'server')


class Message(models.Model):
    """聊天消息"""
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages')
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name='messages')
    reply_to = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.author.username}: {self.content[:30]}'

    class Meta:
        db_table = 'messages'
        ordering = ['created_at']


class ChannelReadState(models.Model):
    """频道已读状态"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='read_states')
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name='read_states')
    last_read_id = models.PositiveBigIntegerField(default=0)

    class Meta:
        db_table = 'channel_read_states'
        unique_together = ('user', 'channel')


class DirectMessage(models.Model):
    """私信"""
    content = models.TextField()
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_dms')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_dms')
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        db_table = 'direct_messages'
        ordering = ['created_at']
