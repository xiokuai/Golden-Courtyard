from rest_framework import viewsets, status, permissions
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError

from .models import User, Server, Channel, Message, Membership, DirectMessage, ChannelReadState
from .serializers import (
    UserSerializer, RegisterSerializer, ServerSerializer,
    ChannelSerializer, MessageSerializer, MembershipSerializer,
    DirectMessageSerializer,
)
from .consumers import online_users


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register_view(request):
    ser = RegisterSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    user = ser.save()
    login(request, user)
    # 自动加入系统服务器
    system_server = Server.objects.filter(is_system=True).first()
    if system_server:
        Membership.objects.get_or_create(user=user, server=system_server, defaults={'role': 'member'})
    return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_view(request):
    username = request.data.get('username')
    password = request.data.get('password')
    user = authenticate(request, username=username, password=password)
    if user is None:
        return Response({'detail': '用户名或密码错误'}, status=status.HTTP_401_UNAUTHORIZED)
    login(request, user)
    return Response(UserSerializer(user).data)


@api_view(['POST'])
def logout_view(request):
    logout(request)
    return Response({'detail': '已登出'})


@api_view(['GET'])
def me_view(request):
    return Response(UserSerializer(request.user).data)


class ServerViewSet(viewsets.ModelViewSet):
    serializer_class = ServerSerializer

    def get_queryset(self):
        return Server.objects.filter(memberships__user=self.request.user)

    def perform_create(self, serializer):
        server = serializer.save(owner=self.request.user)
        Membership.objects.create(user=self.request.user, server=server, role='owner')
        Channel.objects.create(name='综合', server=server)

    def perform_update(self, serializer):
        server = self.get_object()
        if server.owner != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('只有服务器所有者可以修改服务器')
        serializer.save()

    def perform_destroy(self, instance):
        from rest_framework.exceptions import PermissionDenied
        if instance.is_system:
            raise PermissionDenied('不能删除系统服务器')
        if instance.owner != self.request.user:
            raise PermissionDenied('只有服务器所有者可以删除服务器')
        instance.delete()

    @action(detail=False, methods=['post'], url_path='join')
    def join_server(self, request):
        code = request.data.get('invite_code', '')
        try:
            server = Server.objects.get(invite_code=code)
        except Server.DoesNotExist:
            return Response({'detail': '邀请码无效'}, status=status.HTTP_404_NOT_FOUND)
        _, created = Membership.objects.get_or_create(user=request.user, server=server)
        if not created:
            return Response({'detail': '你已经在该服务器中'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ServerSerializer(server).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        server = self.get_object()
        memberships = server.memberships.select_related('user').all()
        return Response(MembershipSerializer(memberships, many=True).data)

    @action(detail=True, methods=['post'], url_path='leave')
    def leave_server(self, request, pk=None):
        server = self.get_object()
        if server.is_system:
            return Response({'detail': '不能退出系统服务器'}, status=status.HTTP_400_BAD_REQUEST)
        if server.owner == request.user:
            return Response({'detail': '所有者不能退出服务器，请先转让或删除'}, status=status.HTTP_400_BAD_REQUEST)
        Membership.objects.filter(user=request.user, server=server).delete()
        return Response({'detail': '已退出服务器'})

    @action(detail=True, methods=['get'], url_path='online')
    def online_members(self, request, pk=None):
        server = self.get_object()
        ids = list(online_users.get(server.id, set()))
        return Response({'online_user_ids': ids})

    @action(detail=True, methods=['post'], url_path='role')
    def change_role(self, request, pk=None):
        """修改成员角色（仅 owner 可操作）"""
        server = self.get_object()
        if server.owner != request.user:
            return Response({'detail': '只有所有者可以修改角色'}, status=status.HTTP_403_FORBIDDEN)
        user_id = request.data.get('user_id')
        new_role = request.data.get('role')
        if new_role not in ('admin', 'member'):
            return Response({'detail': '无效的角色'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            ms = Membership.objects.get(user_id=user_id, server=server)
        except Membership.DoesNotExist:
            return Response({'detail': '该用户不在服务器中'}, status=status.HTTP_404_NOT_FOUND)
        if ms.role == 'owner':
            return Response({'detail': '不能修改所有者的角色'}, status=status.HTTP_400_BAD_REQUEST)
        ms.role = new_role
        ms.save()
        return Response({'detail': f'已设为{ms.get_role_display()}'})

    @action(detail=True, methods=['post'], url_path='kick')
    def kick_member(self, request, pk=None):
        """踢出成员（owner/admin 可操作）"""
        server = self.get_object()
        my_ms = Membership.objects.filter(user=request.user, server=server).first()
        if not my_ms or my_ms.role not in ('owner', 'admin'):
            return Response({'detail': '权限不足'}, status=status.HTTP_403_FORBIDDEN)
        user_id = request.data.get('user_id')
        try:
            target_ms = Membership.objects.get(user_id=user_id, server=server)
        except Membership.DoesNotExist:
            return Response({'detail': '该用户不在服务器中'}, status=status.HTTP_404_NOT_FOUND)
        if target_ms.role == 'owner':
            return Response({'detail': '不能踢出所有者'}, status=status.HTTP_400_BAD_REQUEST)
        if target_ms.role == 'admin' and my_ms.role != 'owner':
            return Response({'detail': '只有所有者可以踢出管理员'}, status=status.HTTP_403_FORBIDDEN)
        target_ms.delete()
        return Response({'detail': '已踢出该成员'})


class ChannelViewSet(viewsets.ModelViewSet):
    serializer_class = ChannelSerializer
    http_method_names = ['get', 'post', 'delete']

    def get_queryset(self):
        return Channel.objects.filter(
            server__memberships__user=self.request.user,
            server_id=self.kwargs.get('server_pk')
        )

    def perform_create(self, serializer):
        from rest_framework.exceptions import PermissionDenied
        server = Server.objects.get(pk=self.kwargs['server_pk'])
        if not Membership.objects.filter(user=self.request.user, server=server).exists():
            raise PermissionDenied('你不是该服务器的成员')
        serializer.save(server=server)

    def perform_destroy(self, instance):
        from rest_framework.exceptions import PermissionDenied
        if instance.server.is_system:
            raise PermissionDenied('不能删除系统服务器的频道')
        membership = Membership.objects.filter(
            user=self.request.user, server=instance.server
        ).first()
        if not membership or membership.role not in ('owner', 'admin'):
            raise PermissionDenied('只有管理员可以删除频道')
        instance.delete()


class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    http_method_names = ['get', 'post', 'delete']
    pagination_class = None

    def get_queryset(self):
        return Message.objects.filter(
            channel_id=self.kwargs.get('channel_pk'),
            channel__server__memberships__user=self.request.user,
        ).select_related('author', 'reply_to', 'reply_to__author')

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        before = request.query_params.get('before')
        if before:
            qs = qs.filter(id__lt=before)
        qs = qs.order_by('-created_at')[:50]
        data = self.get_serializer(reversed(list(qs)), many=True).data
        return Response(data)

    def perform_create(self, serializer):
        serializer.save(
            author=self.request.user,
            channel_id=self.kwargs['channel_pk'],
        )

    def perform_destroy(self, instance):
        from rest_framework.exceptions import PermissionDenied
        if instance.author != self.request.user:
            raise PermissionDenied('只能删除自己的消息')
        instance.delete()


@api_view(['GET'])
def search_users(request):
    q = request.query_params.get('q', '').strip()
    if len(q) < 1:
        return Response([])
    users = User.objects.filter(username__icontains=q).exclude(id=request.user.id)[:10]
    return Response(UserSerializer(users, many=True).data)


@api_view(['GET'])
def dm_conversations(request):
    """获取当前用户的所有私信对话列表"""
    from django.db.models import Q, Max, Count, Subquery, OuterRef, Case, When, F, IntegerField
    user = request.user

    # 用一条查询获取所有对话伙伴 ID
    sent = DirectMessage.objects.filter(sender=user).values_list('receiver_id', flat=True)
    received = DirectMessage.objects.filter(receiver=user).values_list('sender_id', flat=True)
    partner_ids = set(sent) | set(received)

    if not partner_ids:
        return Response([])

    # 批量查询每个伙伴的最后一条消息和未读数
    partners = User.objects.filter(id__in=partner_ids)

    # 子查询：最后一条消息的内容
    last_msg_sub = DirectMessage.objects.filter(
        Q(sender=user, receiver_id=OuterRef('pk')) |
        Q(sender_id=OuterRef('pk'), receiver=user)
    ).order_by('-created_at')

    partners = partners.annotate(
        last_time=Max(
            Case(
                When(Q(sent_dms__receiver=user) | Q(received_dms__sender=user), then=F('sent_dms__created_at')),
                default=None,
            )
        ),
    )

    # 由于 Subquery 对 content 和 unread 分别查询更清晰，这里用两次子查询
    from django.db.models import CharField, Value
    partners = User.objects.filter(id__in=partner_ids).annotate(
        _last_content=Subquery(last_msg_sub.values('content')[:1]),
        _last_time=Subquery(last_msg_sub.values('created_at')[:1]),
        _unread=Count(
            'sent_dms',
            filter=Q(sent_dms__receiver=user, sent_dms__is_read=False),
        ),
    ).order_by(F('_last_time').desc(nulls_last=True))

    result = []
    for p in partners:
        result.append({
            'user': UserSerializer(p).data,
            'last_message': (p._last_content or '')[:50],
            'last_time': p._last_time.isoformat() if p._last_time else '',
            'unread': p._unread,
        })
    return Response(result)


@api_view(['GET', 'POST'])
def dm_messages(request, user_id):
    """获取/发送与某用户的私信"""
    from django.db.models import Q
    try:
        other = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Response({'detail': '用户不存在'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        msgs = DirectMessage.objects.filter(
            (Q(sender=request.user, receiver=other) | Q(sender=other, receiver=request.user))
        ).select_related('sender', 'receiver')
        before = request.query_params.get('before')
        if before:
            msgs = msgs.filter(id__lt=before)
        msgs = msgs.order_by('-created_at')[:50]
        # 标记已读
        DirectMessage.objects.filter(sender=other, receiver=request.user, is_read=False).update(is_read=True)
        return Response(DirectMessageSerializer(list(reversed(list(msgs))), many=True).data)

    else:
        content = request.data.get('content', '').strip()
        if not content:
            return Response({'detail': '内容不能为空'}, status=status.HTTP_400_BAD_REQUEST)
        dm = DirectMessage.objects.create(sender=request.user, receiver=other, content=content)
        return Response(DirectMessageSerializer(dm).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def unread_counts(request):
    """获取当前用户所有频道的未读消息数"""
    from django.db.models import Q, Max, Count, Subquery, OuterRef
    user = request.user
    channels = Channel.objects.filter(server__memberships__user=user)
    result = {}
    for ch in channels:
        state = ChannelReadState.objects.filter(user=user, channel=ch).first()
        last_read = state.last_read_id if state else 0
        count = Message.objects.filter(channel=ch, id__gt=last_read).exclude(author=user).count()
        if count > 0:
            result[ch.id] = count
    return Response(result)


@api_view(['POST'])
def mark_read(request, channel_id):
    """标记频道已读"""
    last_msg = Message.objects.filter(channel_id=channel_id).order_by('-id').first()
    if last_msg:
        ChannelReadState.objects.update_or_create(
            user=request.user, channel_id=channel_id,
            defaults={'last_read_id': last_msg.id},
        )
    return Response({'ok': True})


@api_view(['POST'])
def upload_avatar(request):
    """上传用户头像"""
    file = request.FILES.get('avatar')
    if not file:
        return Response({'detail': '请选择图片'}, status=status.HTTP_400_BAD_REQUEST)
    if file.size > 2 * 1024 * 1024:
        return Response({'detail': '图片不能超过2MB'}, status=status.HTTP_400_BAD_REQUEST)
    user = request.user
    if user.avatar:
        user.avatar.delete(save=False)
    user.avatar = file
    user.save(update_fields=['avatar'])
    return Response(UserSerializer(user).data)


@api_view(['POST'])
def update_status(request):
    """更新用户状态消息"""
    text = request.data.get('status_text', '').strip()[:100]
    request.user.status_text = text
    request.user.save(update_fields=['status_text'])
    return Response(UserSerializer(request.user).data)


@api_view(['POST'])
def upload_server_icon(request, pk):
    """上传服务器图标"""
    try:
        server = Server.objects.get(pk=pk)
    except Server.DoesNotExist:
        return Response({'detail': '服务器不存在'}, status=status.HTTP_404_NOT_FOUND)
    if server.owner != request.user:
        return Response({'detail': '只有所有者可以修改图标'}, status=status.HTTP_403_FORBIDDEN)
    file = request.FILES.get('icon')
    if not file:
        return Response({'detail': '请选择图片'}, status=status.HTTP_400_BAD_REQUEST)
    if file.size > 2 * 1024 * 1024:
        return Response({'detail': '图片不能超过2MB'}, status=status.HTTP_400_BAD_REQUEST)
    if server.icon:
        server.icon.delete(save=False)
    server.icon = file
    server.save(update_fields=['icon'])
    return Response(ServerSerializer(server, context={'request': request}).data)


def _detect_attachment_type(filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext in ('jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg'):
        return 'image'
    if ext in ('mp4', 'webm', 'mov', 'avi', 'mkv'):
        return 'video'
    if ext in ('mp3', 'wav', 'ogg', 'flac', 'aac', 'm4a'):
        return 'audio'
    return 'file'


MAX_UPLOAD = 20 * 1024 * 1024  # 20MB


@api_view(['POST'])
def upload_message_file(request, channel_id):
    """上传文件消息到频道"""
    try:
        channel = Channel.objects.select_related('server').get(pk=channel_id)
    except Channel.DoesNotExist:
        return Response({'detail': '频道不存在'}, status=status.HTTP_404_NOT_FOUND)
    if not Membership.objects.filter(user=request.user, server=channel.server).exists():
        return Response({'detail': '你不是该服务器的成员'}, status=status.HTTP_403_FORBIDDEN)
    file = request.FILES.get('file')
    if not file:
        return Response({'detail': '请选择文件'}, status=status.HTTP_400_BAD_REQUEST)
    if file.size > MAX_UPLOAD:
        return Response({'detail': '文件不能超过20MB'}, status=status.HTTP_400_BAD_REQUEST)
    content = request.POST.get('content', '')
    reply_to_id = request.POST.get('reply_to')
    att_type = _detect_attachment_type(file.name)
    kwargs = dict(
        content=content, author=request.user, channel=channel,
        attachment=file, attachment_type=att_type, attachment_name=file.name,
    )
    if reply_to_id:
        kwargs['reply_to_id'] = int(reply_to_id)
    msg = Message.objects.create(**kwargs)
    # 通过 channel layer 广播给 WebSocket 房间
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    layer = get_channel_layer()
    att_url = request.build_absolute_uri(msg.attachment.url) if msg.attachment else ''
    broadcast = {
        'id': msg.id, 'content': msg.content,
        'author': {'id': request.user.id, 'username': request.user.username,
                   'avatar': request.user.avatar.url if request.user.avatar else ''},
        'channel': msg.channel_id,
        'attachment': att_url, 'attachment_type': att_type, 'attachment_name': file.name,
        'reply_to': None, 'created_at': msg.created_at.isoformat(),
    }
    if msg.reply_to_id:
        rt = Message.objects.select_related('author').filter(pk=msg.reply_to_id).first()
        if rt:
            broadcast['reply_to'] = {'id': rt.id, 'content': rt.content,
                                     'author': {'id': rt.author.id, 'username': rt.author.username}}
    async_to_sync(layer.group_send)(f'chat_{channel_id}', {
        'type': 'chat_message', 'message': broadcast,
    })
    return Response({'ok': True, 'id': msg.id}, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def upload_dm_file(request, user_id):
    """上传文件私信"""
    try:
        receiver = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Response({'detail': '用户不存在'}, status=status.HTTP_404_NOT_FOUND)
    file = request.FILES.get('file')
    if not file:
        return Response({'detail': '请选择文件'}, status=status.HTTP_400_BAD_REQUEST)
    if file.size > MAX_UPLOAD:
        return Response({'detail': '文件不能超过20MB'}, status=status.HTTP_400_BAD_REQUEST)
    content = request.POST.get('content', '')
    att_type = _detect_attachment_type(file.name)
    dm = DirectMessage.objects.create(
        sender=request.user, receiver=receiver, content=content,
        attachment=file, attachment_type=att_type, attachment_name=file.name,
    )
    att_url = request.build_absolute_uri(dm.attachment.url) if dm.attachment else ''
    broadcast = {
        'id': dm.id, 'content': dm.content,
        'sender': {'id': request.user.id, 'username': request.user.username},
        'receiver': {'id': receiver.id, 'username': receiver.username},
        'attachment': att_url, 'attachment_type': att_type, 'attachment_name': dm.attachment_name,
        'created_at': dm.created_at.isoformat(),
    }
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    layer = get_channel_layer()
    async_to_sync(layer.group_send)(f'dm_{receiver.id}', {'type': 'dm_message', 'message': broadcast})
    async_to_sync(layer.group_send)(f'dm_{request.user.id}', {'type': 'dm_message', 'message': broadcast})
    return Response({'ok': True, 'id': dm.id}, status=status.HTTP_201_CREATED)
