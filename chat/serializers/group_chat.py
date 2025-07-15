from rest_framework import serializers
from chat.models import (
    GroupChatRoom,
    GroupMember,
)
from django.contrib.auth import get_user_model

User = get_user_model()


class UserPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']
        read_only_fields = ['id', 'username']


class GroupMemberSerializer(serializers.ModelSerializer):
    """Serializer for group members with user details"""
    user = UserPublicSerializer(read_only=True)
    user_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = GroupMember
        fields = [
            'id',
            'user',
            'user_id',
            'role',
            'can_invite_others',
            'joined_at',
            'is_admin',
            'is_moderator'
        ]
        read_only_fields = ['id', 'joined_at', 'is_admin', 'is_moderator']

    def validate_user_id(self, value):
        request = self.context.get('request')
        if request and request.user.id == value:
            raise serializers.ValidationError("You are already a member of this group.")


        """Ensure the user exists"""
        try:
            User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User does not exist.")
        return value

    def validate_role(self, value):
        if value not in dict(GroupMember.ROLE_CHOICES):
            raise serializers.ValidationError("Invalid role selected.")
        return value

    def validate(self, data):
        """Prevent duplicate membership"""
        group = self.context.get('group')
        user_id = data.get('user_id')


        if not group or not user_id:
            return data

        
        existing_member = GroupMember.objects.filter(group=group, user_id=user_id)
        if self.instance:
                existing_member = existing_member.exclude(id=self.instance.id)
        if existing_member.exists():
            raise serializers.ValidationError("User is already a member of this group.")
        
         # Check if group is full
        if group.is_full:
            raise serializers.ValidationError("This group is full. No more members can be added.")

        return data


class GroupChatRoomSerializer(serializers.ModelSerializer):
    """Main serializer for group chat rooms"""
    created_by = UserPublicSerializer(read_only=True)
    max_members = serializers.ReadOnlyField()
    member_count = serializers.ReadOnlyField()
    is_full = serializers.ReadOnlyField()
    members = GroupMemberSerializer(many=True, read_only=True)

    class Meta:
        model = GroupChatRoom
        fields = [
            'id',
            'name',
            'description',
            'created_by',
            'is_private',
            'max_members',
            'is_active',
            'created_at',
            'updated_at',
            'member_count',
            'is_full',
            'members'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'member_count', 'is_full']

    def validate_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError("Group name cannot be empty.")

        if value.isdigit():
            raise serializers.ValidationError("Group name cannot be purely numeric.")

        if len(value) > 20:
            raise serializers.ValidationError("Group name cannot exceed 20 characters.")

        if len(value) < 2:
            raise serializers.ValidationError("Group name must be at least 2 characters long.")

        return value

    

    def validate_description(self, value):
        if value is None:
            return value

        value = value.strip()
        if len(value) > 300:  # corrected limit
            raise serializers.ValidationError("Description cannot exceed 300 characters.")
        return value if value else None

    def validate_is_private(self, value):
        if not isinstance(value, bool):
            raise serializers.ValidationError("Privacy setting must be a boolean.")
        return value

    def validate(self, data):
        request = self.context.get('request')
        name = data.get('name')

        if request and request.user:
            # Limit total active groups per user
            active_groups = GroupChatRoom.objects.filter(created_by=request.user, is_active=True)
            if not self.instance and active_groups.count() >= 10:
                raise serializers.ValidationError("You cannot create more than 10 active groups.")

            # Check for duplicate group name by user
            if name and GroupChatRoom.objects.filter(
                created_by=request.user,
                name__iexact=name,
                is_active=True
            ).exclude(id=getattr(self.instance, 'id', None)).exists():
                raise serializers.ValidationError("You already have a group with this name.")

        return data
