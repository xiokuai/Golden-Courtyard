from rest_framework import serializers
from .models import User, Server, Channel, Message, Membership, DirectMessage


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'avatar', 'online']


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

    class Meta:
        model = Server
        fields = ['id', 'name', 'icon', 'owner', 'invite_code', 'channels', 'member_count', 'created_at']
        read_only_fields = ['invite_code', 'created_at']

    def get_member_count(self, obj):
        return obj.memberships.count()


class MessageSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'content', 'author', 'channel', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class DirectMessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    receiver = UserSerializer(read_only=True)
    receiver_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = DirectMessage
        fields = ['id', 'content', 'sender', 'receiver', 'receiver_id', 'created_at', 'is_read']
        read_only_fields = ['created_at', 'is_read']
