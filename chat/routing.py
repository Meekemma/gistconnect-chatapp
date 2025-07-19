from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Private chat route
    re_path(r'ws/chat/(?P<room_name>\w+)/$', consumers.ChatConsumer.as_asgi()),

    # Group chat route
    re_path(r'ws/group-chat/(?P<group_id>[0-9a-f-]+)/$', consumers.GroupChatConsumer.as_asgi()),
]
