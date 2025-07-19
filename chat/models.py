from django.db import models
from django.utils import timezone
from django.core.validators import FileExtensionValidator
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()

class PrivateChatRoom(models.Model):
    participant_1 = models.ForeignKey(User, related_name='participant1', on_delete=models.CASCADE)
    participant_2 = models.ForeignKey(User, related_name='participant2', on_delete=models.CASCADE)
    is_deleted_for_participant_1 = models.BooleanField(default=False)
    is_deleted_for_participant_2 = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Private Chat Room'
        verbose_name_plural = 'Private Chat Rooms'
        ordering = ['-created_at']
        unique_together = ('participant_1', 'participant_2')

    def __str__(self):
        return f"Chat between {self.participant_1.username} and {self.participant_2.username}"


    #Enforcing unique chat rooms between two users i.e A-B is the same as B-A
    def save(self, *args, **kwargs):
        # Ensure participant_1 is always the user with the lower ID
        if self.participant_1.id > self.participant_2.id:
            self.participant_1, self.participant_2 = self.participant_2, self.participant_1
        super().save(*args, **kwargs)


class Message(models.Model):
    conversation = models.ForeignKey(PrivateChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages_sent')
    content = models.TextField()
    is_archived = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"Message from {self.sender.username} at {self.timestamp}"




MAX_GROUP_MEMBERS = 250

class GroupChatRoom(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_groups')
    is_private = models.BooleanField(default=False)
    max_members = models.PositiveIntegerField(default=250, editable=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Group Chat Room'
        verbose_name_plural = 'Group Chat Rooms'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['created_at']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.name

    @property
    def member_count(self):
        return self.members.count()

    @property
    def is_full(self):
        return self.member_count >= self.max_members


class GroupMember(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('moderator', 'Moderator'),
        ('member', 'Member'),
    ]

    group = models.ForeignKey(GroupChatRoom, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    can_invite_others = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Group Member'
        verbose_name_plural = 'Group Members'
        ordering = ['-joined_at']
        unique_together = ('group', 'user')
        indexes = [
            models.Index(fields=['group', 'role']),
            models.Index(fields=['user']),
            models.Index(fields=['joined_at']),
        ]

    def __str__(self):
        return f"{self.user.username} ({self.role}) in {self.group.name}"

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_moderator(self):
        return self.role in ['admin', 'moderator']


class GroupMessage(models.Model):
    MESSAGE_TYPE_CHOICES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('doc', 'Doc'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(GroupChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='group_messages_sent')
    content = models.TextField()
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPE_CHOICES, default='text')
    doc = models.FileField(upload_to='group_messages/files/', null=True, blank=True,
                            validators=[FileExtensionValidator(allowed_extensions=['pdf', 'docx', 'xlsx', 'zip', 'mp4'])])
    image = models.ImageField(upload_to='group_messages/images/', null=True, blank=True)

    reply_to = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='replies')
    timestamp = models.DateTimeField(auto_now_add=True)
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Group Message'
        verbose_name_plural = 'Group Messages'
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['group', 'timestamp']),
            models.Index(fields=['sender', 'timestamp']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['message_type']),
        ]

    def __str__(self):
        sender_name = self.sender.username if self.sender else 'Deleted User'
        return f"Message by {sender_name} in {self.group.name} at {self.timestamp}"

    @property
    def is_reply(self):
        return self.reply_to is not None


class GroupMessageReadStatus(models.Model):
    """Track read status per user per message"""
    message = models.ForeignKey(GroupMessage, on_delete=models.CASCADE, related_name='read_statuses')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='message_read_statuses')
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Group Message Read Status'
        verbose_name_plural = 'Group Message Read Statuses'
        unique_together = ('message', 'user')
        indexes = [
            models.Index(fields=['message', 'user']),
            models.Index(fields=['user', 'read_at']),
        ]

    def __str__(self):
        return f"{self.user.username} read message {self.message.id}"


class GroupInvitation(models.Model):
    """Handle group invitations"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('expired', 'Expired'),
    ]

    group = models.ForeignKey(GroupChatRoom, on_delete=models.CASCADE, related_name='invitations')
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_invitations')
    invited_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_invitations')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Group Invitation'
        verbose_name_plural = 'Group Invitations'
        ordering = ['-created_at']
        unique_together = ('group', 'invited_user')
        indexes = [
            models.Index(fields=['invited_user', 'status']),
            models.Index(fields=['group', 'status']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"Invitation to {self.invited_user.username} for {self.group.name}"

    @property
    def is_expired(self):
        if self.expires_at:
            
            return timezone.now() > self.expires_at
        return False