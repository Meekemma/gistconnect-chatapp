from django.urls import path
from chat.views import private_views, group_views

urlpatterns = [
    path('start-chat/', private_views.start_private_chat, name='start-private-chat'),
    path('my-chats/', private_views.get_user_chats, name='get-user-chats'),
    path('total-unread/', private_views.total_unread_count, name='total-unread-count'),
    path('delete-chat/<str:room_id>/', private_views.delete_chat_room, name='delete-chat-room'),
    path('chat-messages/<str:room_id>/', private_views.get_user_message, name='get-chat-messages'),

    path('groups/', group_views.group_chat_list_create_view, name='group-list-create'),
    path('groups/<uuid:group_id>/', group_views.group_chat_detail_view, name='group-detail'),
    path('groups/<uuid:group_id>/add-member/', group_views.add_group_member, name='add-group-member'),
    path('groups/<uuid:group_id>/remove-member/', group_views.remove_member_by_admin, name='remove-group-member'),
    path('groups/<uuid:group_id>/leave-member/', group_views.leave_group, name='leave-group'),
    path('groups/<uuid:group_id>/messages/', group_views.get_group_messages, name='group-messages'),
    path('groups/<uuid:group_id>/upload/', group_views.GroupFileUpload, name='group-upload'),
    path('groups/<uuid:group_id>/delete-message/', group_views.delete_messages, name='group-delete-message'),

]
