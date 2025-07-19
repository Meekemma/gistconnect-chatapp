import uuid
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from rest_framework import status
from django.db.models import Q
from django.contrib.auth import get_user_model
from ..models import *
from chat.serializers import GroupMemberSerializer,GroupChatRoomSerializer,GroupMessageSerializer

User = get_user_model()

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

# chat/views/group.py



@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def group_chat_list_create_view(request):
    """List groups user belongs to, or create a new group"""
    if request.method == 'GET':
        groups = GroupChatRoom.objects.filter(
            members__user=request.user,
            is_active=True
        ).distinct()
        serializer = GroupChatRoomSerializer(groups, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = GroupChatRoomSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            group = serializer.save(created_by=request.user)
            GroupMember.objects.create(
                group=group,
                user=request.user,
                role='admin',
                can_invite_others=True
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




@api_view(['GET', 'DELETE'])
@permission_classes([IsAuthenticated])
def group_chat_detail_view(request, group_id):
    """Retrieve or soft-delete a group"""
    group = get_object_or_404(GroupChatRoom, id=group_id, is_active=True)

    if request.method == 'GET':
        if not GroupMember.objects.filter(group=group, user=request.user).exists():
            return Response({'detail': 'Access denied.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = GroupChatRoomSerializer(group)
        return Response(serializer.data)

    elif request.method == 'DELETE':
        if group.created_by != request.user:
            return Response({'detail': 'Only the group creator can delete this group.'}, status=status.HTTP_403_FORBIDDEN)
        group.is_active = False
        group.save()
        return Response({'message': 'Group deleted successfully'}, status=status.HTTP_204_NO_CONTENT)




@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_group_member(request, group_id):
    group = get_object_or_404(GroupChatRoom, id=group_id)

    # Ensure request.user is part of the group
    requester = GroupMember.objects.filter(group=group, user=request.user).first()
    if not requester or not requester.can_invite_others:
        return Response({"detail": "You don't have permission to add members."}, status=status.HTTP_403_FORBIDDEN)
    

    data = request.data.copy()
    data['group'] = str(group.id)  # Inject group ID

    serializer = GroupMemberSerializer(data=data, context={'group': group})

    if serializer.is_valid(raise_exception=True):
        serializer.save(group=group)
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)





@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_member_role(request, group_id):
    group = get_object_or_404(GroupChatRoom, id=group_id)

    requester = GroupMember.objects.filter(group=group, user=request.user).first()
    if not requester or not requester.role == 'admin':
        return Response({"detail": "You don't have permission to update members role."}, status=status.HTTP_403_FORBIDDEN)


    if request.method == 'PUT' or request.method == 'PATCH':
        serializer= GroupMemberSerializer(requester)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)



@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_member_by_admin(request, group_id):
    group = get_object_or_404(GroupChatRoom, id=group_id)
    user_id = request.data.get('user_id')

    if not user_id:
        return Response({'detail': 'user_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

    # Ensure requester is an admin in this group
    try:
        requester = GroupMember.objects.get(group=group, user=request.user)
    except GroupMember.DoesNotExist:
        return Response(
            {"detail": "You are not a member of this group."},
            status=status.HTTP_403_FORBIDDEN
        )

    if requester.role != 'admin':
        return Response(
            {"detail": "Only admins can remove members from this group."},
            status=status.HTTP_403_FORBIDDEN
        )

    # Try to get the member being removed
    try:
        member = GroupMember.objects.get(group=group, user_id=user_id)
    except GroupMember.DoesNotExist:
        return Response({"detail": "User is not a member of this group."}, status=status.HTTP_404_NOT_FOUND)

    # Prevent admin from removing themselves (optional)
    if member.user == request.user:
        return Response({"detail": "You cannot remove yourself from the group."}, status=status.HTTP_400_BAD_REQUEST)

    member.delete()
    return Response({'message': 'User successfully removed from the group'}, status=status.HTTP_204_NO_CONTENT)







@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def leave_group(request, group_id):
    group = get_object_or_404(GroupChatRoom, id=group_id)

    try:
        member = GroupMember.objects.get(group=group, user=request.user)
    except GroupMember.DoesNotExist:
        return Response({"detail": "You are not a member of this group."}, status=status.HTTP_404_NOT_FOUND)

    if member.role == 'admin':
        return Response({"detail": "Admins cannot leave the group. Please assign another admin first."},
                        status=status.HTTP_403_FORBIDDEN)

    member.delete()
    return Response({'message': 'You have successfully left the group.'}, status=status.HTTP_204_NO_CONTENT)






@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_group_messages(request, group_id):
    group = get_object_or_404(GroupChatRoom, id=group_id)

    # Check if the user is a member via GroupMember model
    is_member = GroupMember.objects.filter(group=group, user=request.user).exists()
    if not is_member:
        return Response({"detail": "You are not a member of this group."}, status=403)

    messages = GroupMessage.objects.filter(group=group).select_related('sender', 'reply_to').order_by('timestamp')
    serializer = GroupMessageSerializer(messages, many=True)
    return Response(serializer.data)





@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def GroupFileUpload(request, group_id):
    user = request.user
    group = get_object_or_404(GroupChatRoom, id=group_id)

    doc = request.FILES.get('doc')
    image = request.FILES.get('image')
    caption = request.data.get('caption', '')

    if not doc and not image:
        return Response({'error': 'No file or image provided.'}, status=400)

    message_type = 'doc' if doc else 'image'

    # Save message
    message = GroupMessage.objects.create(
        group=group,
        sender=user,
        message_type=message_type,
        doc=doc if doc else None,
        image=image if image else None,
        content=caption
    )

    # Broadcast to WebSocket group
    channel_layer = get_channel_layer()
    file_url = request.build_absolute_uri(message.doc.url if message_type == 'doc' else message.image.url)

    async_to_sync(channel_layer.group_send)(
        f"group_{group_id}",
        {
            'type': 'group_message',
            'message_id': str(message.id),
            'message': caption,
            'file_url': file_url,
            'sender_id': str(user.id),
            'sender_username': user.username,
            'message_type': message_type,
            'timestamp': message.timestamp.isoformat(),
            'reply_to': None
        }
    )

    return Response({
        "id": str(message.id),
        "type": message.message_type,
        "url": file_url,
        "caption": caption,
        "timestamp": message.timestamp
    })




@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_messages(request, group_id):
    group = get_object_or_404(GroupChatRoom, id=group_id)

    message_id = request.data.get('message_id')
    if not message_id:
        return Response({'detail': 'Message ID is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        message = GroupMessage.objects.get(id=message_id,  group=group, sender=request.user)
        message.delete()
        return Response({'detail': 'Message deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
    except GroupMessage.DoesNotExist:
        return Response({'detail': 'Message not found or not owned by user'}, status=status.HTTP_404_NOT_FOUND)
