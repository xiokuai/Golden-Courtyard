from rest_framework import viewsets, status, permissions
from rest_framework.decorators import api_view, permission_classes, action
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
        if instance.owner != self.request.user:
            from rest_framework.exceptions import PermissionDenied
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
