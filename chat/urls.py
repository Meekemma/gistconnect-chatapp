from django.urls import path
from . import views

urlpatterns = [
    path('start-chat/', views.start_private_chat, name='start-private-chat'),
    path('my-chats/', views.get_user_chats, name='get-user-chats'),
    path('total-unread/', views.total_unread_count, name='total-unread-count'),
    path('delete-chat/<str:room_id>/', views.delete_chat_room, name='delete-chat-room'),
    path('chat-messages/<str:room_id>/', views.get_user_message, name='get-chat-messages'),

]
