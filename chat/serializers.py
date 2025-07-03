from rest_framework import serializers
from .models import PrivateChatRoom, Message
from django.contrib.auth import get_user_model

User = get_user_model()

# Public serializer for user (used in message display)
class UserPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']
        read_only_fields = ['id', 'username']


# Chat room serializer
class PrivateChatRoomSerializer(serializers.ModelSerializer):
    participant_1 = serializers.SlugRelatedField(slug_field='username', read_only=True)
    participant_2 = serializers.SlugRelatedField(slug_field='username', read_only=True)
    unread_count = serializers.SerializerMethodField()


    class Meta:
        model = PrivateChatRoom
        fields = ['id', 'participant_1', 'participant_2', 'created_at', 'unread_count']
        read_only_fields = ['id', 'created_at']

    def get_unread_count(self, obj):
        user = self.context['request'].user
        return obj.messages.filter(is_read=False).exclude(sender=user).count()


# Message serializer for both read and write
class MessageSerializer(serializers.ModelSerializer):
    # For writing
    conversation_id = serializers.PrimaryKeyRelatedField(
        source='conversation',
        queryset=PrivateChatRoom.objects.all(),
        write_only=True
    )
    sender_id = serializers.PrimaryKeyRelatedField(
        source='sender',
        queryset=User.objects.all(),
        write_only=True
    )

    # For reading
    sender = UserPublicSerializer(read_only=True)
    conversation = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Message
        fields = [
            'id',
            'conversation_id',  # Used on creation
            'conversation',     # Used on read
            'sender_id',        # Used on creation
            'sender',           # Used on read
            'content',
            'is_archived',
            'timestamp',
            'is_read'
        ]
        read_only_fields = ['id', 'timestamp', 'conversation', 'sender']
