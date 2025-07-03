from django.contrib import admin
from .models import PrivateChatRoom, Message


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
