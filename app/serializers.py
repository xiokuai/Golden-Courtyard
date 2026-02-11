from rest_framework import serializers
from .models import User, Server, Channel, Message, Membership, DirectMessage


class UserSerializer(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'avatar', 'online', 'status_text']

    def get_avatar(self, obj):
        if obj.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return ''


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ['id', 'username', 'password']

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class ChannelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Channel
        fields = ['id', 'name', 'channel_type', 'server', 'created_at']
        read_only_fields = ['created_at']


class MembershipSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Membership
        fields = ['id', 'user', 'role', 'joined_at']


class ServerSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    channels = ChannelSerializer(many=True, read_only=True)
    member_count = serializers.SerializerMethodField()
    icon = serializers.SerializerMethodField()

    class Meta:
        model = Server
        fields = ['id', 'name', 'icon', 'owner', 'invite_code', 'channels', 'member_count', 'is_system', 'created_at']
        read_only_fields = ['invite_code', 'created_at']

    def get_member_count(self, obj):
        return obj.memberships.count()

    def get_icon(self, obj):
        if obj.icon:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.icon.url)
            return obj.icon.url
        return ''


class ReplyInfoSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'content', 'author']


class MessageSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    reply_to = ReplyInfoSerializer(read_only=True)
    reply_to_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    attachment = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ['id', 'content', 'author', 'channel', 'reply_to', 'reply_to_id',
                  'attachment', 'attachment_type', 'attachment_name', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def get_attachment(self, obj):
        if obj.attachment:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.attachment.url)
            return obj.attachment.url
        return ''


class DirectMessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    receiver = UserSerializer(read_only=True)
    receiver_id = serializers.IntegerField(write_only=True)
    attachment = serializers.SerializerMethodField()

    class Meta:
        model = DirectMessage
        fields = ['id', 'content', 'sender', 'receiver', 'receiver_id',
                  'attachment', 'attachment_type', 'attachment_name', 'created_at', 'is_read']
        read_only_fields = ['created_at', 'is_read']

    def get_attachment(self, obj):
        if obj.attachment:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.attachment.url)
            return obj.attachment.url
        return ''
