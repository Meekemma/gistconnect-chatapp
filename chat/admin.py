from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import PrivateChatRoom, Message, GroupChatRoom, GroupMember, GroupMessage, GroupMessageReadStatus, GroupInvitation


@admin.register(PrivateChatRoom)
class PrivateChatRoomAdmin(admin.ModelAdmin):
    list_display = ('id', 'participant_1', 'participant_2', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('participant_1__username', 'participant_2__username')
    ordering = ('-created_at',)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'sender', 'content_preview', 'is_read', 'is_archived', 'timestamp')
    list_filter = ('is_read', 'is_archived', 'timestamp')
    search_fields = ('sender__username', 'content')
    ordering = ('-timestamp',)

    def content_preview(self, obj):
        return (obj.content[:50] + '...') if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Message Preview'









@admin.register(GroupChatRoom)
class GroupChatRoomAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_by', 'member_count_display', 'is_private', 'is_active', 'created_at']
    list_filter = ['is_private', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'created_by__username']
    readonly_fields = ['id', 'created_at', 'updated_at', 'member_count_display']
    list_per_page = 25
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'created_by')
        }),
        ('Settings', {
            'fields': ('is_private', 'is_active')  
        }),
        ('System Info', {
            'fields': ('id', 'created_at', 'updated_at', 'member_count_display'),
            'classes': ('collapse',)
        }),
    )
    
    def member_count_display(self, obj):
        count = obj.member_count
        return format_html(
            '<span style="color: {};">{}/{}</span>',
            'red' if obj.is_full else 'green',
            count,
            obj.max_members
        )
    member_count_display.short_description = 'Members'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('created_by')



class GroupMemberInline(admin.TabularInline):
    model = GroupMember
    extra = 0
    readonly_fields = ['joined_at']
    fields = ['user', 'role', 'can_invite_others', 'joined_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(GroupMember)
class GroupMemberAdmin(admin.ModelAdmin):
    list_display = ['user', 'group', 'role', 'can_invite_others', 'joined_at']
    list_filter = ['role', 'can_invite_others', 'joined_at']
    search_fields = ['user__username', 'user__email', 'group__name']
    readonly_fields = ['joined_at']
    list_per_page = 50
    date_hierarchy = 'joined_at'
    
    fieldsets = (
        ('Member Information', {
            'fields': ('group', 'user', 'role', 'can_invite_others')
        }),
        ('Timestamps', {
            'fields': ('joined_at',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'group')


@admin.register(GroupMessage)
class GroupMessageAdmin(admin.ModelAdmin):
    list_display = ['id','sender', 'group', 'message_preview', 'message_type','doc', 'image', 'is_reply', 'is_edited', 'timestamp']
    list_filter = ['message_type', 'is_edited', 'timestamp', 'group']
    search_fields = ['content', 'sender__username', 'group__name']
    readonly_fields = ['timestamp', 'edited_at', 'is_reply']
    list_per_page = 50
    date_hierarchy = 'timestamp'
    raw_id_fields = ['reply_to']
    
    fieldsets = (
        ('Message Content', {
            'fields': ('group', 'sender', 'content', 'message_type')
        }),
        ('Threading', {
            'fields': ('reply_to',),
            'classes': ('collapse',)
        }),
        ('Edit History', {
            'fields': ('is_edited', 'edited_at'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('timestamp',),
            'classes': ('collapse',)
        }),
    )
    
    def message_preview(self, obj):
        if len(obj.content) > 50:
            return obj.content[:50] + '...'
        return obj.content
    message_preview.short_description = 'Preview'
    
    def is_reply(self, obj):
        return obj.reply_to is not None
    is_reply.boolean = True
    is_reply.short_description = 'Reply'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('sender', 'group', 'reply_to')


class GroupMessageReadStatusInline(admin.TabularInline):
    model = GroupMessageReadStatus
    extra = 0
    readonly_fields = ['read_at']
    fields = ['user', 'read_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(GroupMessageReadStatus)
class GroupMessageReadStatusAdmin(admin.ModelAdmin):
    list_display = ['user', 'message_group', 'message_preview', 'read_at']
    list_filter = ['read_at']
    search_fields = ['user__username', 'message__content', 'message__group__name']
    readonly_fields = ['read_at']
    list_per_page = 100
    date_hierarchy = 'read_at'
    
    fieldsets = (
        ('Read Status', {
            'fields': ('message', 'user', 'read_at')
        }),
    )
    
    def message_group(self, obj):
        return obj.message.group.name
    message_group.short_description = 'Group'
    
    def message_preview(self, obj):
        content = obj.message.content
        if len(content) > 30:
            return content[:30] + '...'
        return content
    message_preview.short_description = 'Message'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'message', 'message__group')


@admin.register(GroupInvitation)
class GroupInvitationAdmin(admin.ModelAdmin):
    list_display = ['invited_user', 'group', 'invited_by', 'status', 'is_expired_display', 'created_at']
    list_filter = ['status', 'created_at', 'expires_at']
    search_fields = ['invited_user__username', 'invited_by__username', 'group__name']
    readonly_fields = ['created_at', 'responded_at', 'is_expired_display']
    list_per_page = 50
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Invitation Details', {
            'fields': ('group', 'invited_by', 'invited_user', 'status')
        }),
        ('Timing', {
            'fields': ('expires_at', 'created_at', 'responded_at', 'is_expired_display'),
            'classes': ('collapse',)
        }),
    )
    
    def is_expired_display(self, obj):
        if obj.expires_at:
            expired = obj.is_expired
            return format_html(
                '<span style="color: {};">{}</span>',
                'red' if expired else 'green',
                'Expired' if expired else 'Active'
            )
        return 'No Expiry'
    is_expired_display.short_description = 'Expiry Status'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('invited_user', 'invited_by', 'group')
    
    actions = ['mark_as_expired', 'mark_as_pending']
    
    def mark_as_expired(self, request, queryset):
        updated = queryset.update(status='expired')
        self.message_user(request, f'{updated} invitations marked as expired.')
    mark_as_expired.short_description = 'Mark selected invitations as expired'
    
    def mark_as_pending(self, request, queryset):
        updated = queryset.update(status='pending')
        self.message_user(request, f'{updated} invitations marked as pending.')
    mark_as_pending.short_description = 'Mark selected invitations as pending'


# Add inlines to GroupChatRoom admin
GroupChatRoomAdmin.inlines = [GroupMemberInline]

# Add inlines to GroupMessage admin  
GroupMessageAdmin.inlines = [GroupMessageReadStatusInline]
