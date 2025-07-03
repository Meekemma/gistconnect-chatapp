import uuid
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.db.models import Q
from django.contrib.auth import get_user_model
from .models import *
from .serializers import PrivateChatRoomSerializer,MessageSerializer

User = get_user_model()






@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_private_chat(request):
    user = request.user
    other_user_id = request.data.get('user_id')

    if not other_user_id:
        return Response({"error": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    # Ensure UUID format
    try:
        other_user_uuid = uuid.UUID(other_user_id)
    except ValueError:
        return Response({"error": "Invalid UUID format for user_id."}, status=status.HTTP_400_BAD_REQUEST)

    if str(user.id) == str(other_user_uuid):
        return Response({"error": "You cannot start a chat with yourself."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        other_user = User.objects.get(id=other_user_uuid)
    except User.DoesNotExist:
        return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

    # Ensure consistent participant ordering
    participant_1, participant_2 = sorted([user, other_user], key=lambda u: str(u.id))

    room, created = PrivateChatRoom.objects.get_or_create(
        participant_1=participant_1,
        participant_2=participant_2
    )

    serializer = PrivateChatRoomSerializer(room)
    return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_chat_room(request, room_id):
    try:
        room = PrivateChatRoom.objects.get(id=room_id)
    except PrivateChatRoom.DoesNotExist:
        return Response({'error': 'Chat room does not exist'}, status=status.HTTP_404_NOT_FOUND)

    user = request.user

    if user == room.participant_1:
        room.is_deleted_for_participant_1 = True
    elif user == room.participant_2:
        room.is_deleted_for_participant_2 = True
    else:
        return Response({'error': 'You are not a participant of this chat'}, status=status.HTTP_403_FORBIDDEN)

    # If both participants have deleted, delete permanently
    if room.is_deleted_for_participant_1 and room.is_deleted_for_participant_2:
        room.delete()
        return Response({'message': 'Chat deleted permanently for both users'}, status=status.HTTP_204_NO_CONTENT)
    else:
        room.save()
        return Response({'message': 'Chat hidden for you'}, status=status.HTTP_200_OK)




@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_chats(request):
    rooms = PrivateChatRoom.objects.filter(
        Q(participant_1=request.user, is_deleted_for_participant_1=False) |
        Q(participant_2=request.user, is_deleted_for_participant_2=False)
    )
    serializer = PrivateChatRoomSerializer(rooms, many=True, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)




@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_message(request, room_id):
    try:
        room = PrivateChatRoom.objects.get(id=room_id)
    except PrivateChatRoom.DoesNotExist:
        return Response({'error': 'Chat room does not exist'}, status=status.HTTP_404_NOT_FOUND)
    
    # Ensure the requesting user is part of the chat
    if room.participant_1 != request.user and room.participant_2 != request.user:
        return Response({'error': 'You are not authorized to view this chat'}, status=status.HTTP_403_FORBIDDEN)

    # ✅ Mark all unread messages sent to this user as read
    room.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)

    # ✅ Get all messages in order
    messages = room.messages.all().order_by('-timestamp')

    serializer = MessageSerializer(messages, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def total_unread_count(request):
    count = Message.objects.filter(
        conversation__in = PrivateChatRoom.objects.filter(
            Q(participant_1=request.user, is_deleted_for_participant_1=False) |
            Q(participant_2=request.user, is_deleted_for_participant_2=False)
        ),
        is_read=False
    ).exclude(sender=request.user).count()

    return Response({'total_unread': count})

