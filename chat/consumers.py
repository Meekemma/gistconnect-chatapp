from channels.generic.websocket import AsyncWebsocketConsumer
import json
import logging
from .models import PrivateChatRoom, Message
from django.contrib.auth import get_user_model
from channels.db import database_sync_to_async

User = get_user_model()
logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'

        logger.info(f"Connection attempt for room: {self.room_name}, user: {user}")

        if not user.is_authenticated:
            logger.warning("User not authenticated")
            await self.close()
            return

        # Check if conversation exists
        conversation = await self.get_conversation(self.room_name)
        if conversation is None:
            logger.error(f"Conversation with ID {self.room_name} not found")
            await self.close()
            return

        # Verify user is part of the conversation
        if not await self.user_in_conversation(user, self.room_name):
            logger.warning(f"User {user.id} not authorized for room {self.room_name}")
            await self.close()
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
        logger.info(f"WebSocket connection accepted for user {user.id} in room {self.room_name}")

    async def disconnect(self, close_code):
        logger.info(f"WebSocket disconnected with code: {close_code}")
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        user = self.scope["user"]
        if not user.is_authenticated:
            return

        try:
            data = json.loads(text_data)
            message = data.get('message')
            logger.info(f"Received message from {user.id}: {message}")

            # Save message
            conversation = await self.get_conversation(self.room_name)
            if conversation is None:
                logger.error(f"Conversation {self.room_name} not found when saving message")
                return

            message_instance = await self.save_message(conversation, user, message)

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message_instance.content,
                    'sender_id': str(user.id),  # Ensure string format
                    'timestamp': message_instance.timestamp.isoformat()
                }
            )
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON received: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'sender_id': event['sender_id'],
            'timestamp': event['timestamp']
        }))

    # ---------- Database Operations (async-safe) ----------

    @database_sync_to_async
    def get_conversation(self, room_id):
        try:
            logger.info(f"Looking for conversation with ID: {room_id}")
            return PrivateChatRoom.objects.get(id=room_id)
        except PrivateChatRoom.DoesNotExist:
            logger.error(f"PrivateChatRoom with ID {room_id} does not exist")
            return None
        except Exception as e:
            logger.error(f"Error getting conversation {room_id}: {e}")
            return None

    @database_sync_to_async
    def save_message(self, conversation, sender, content):
        try:
            return Message.objects.create(
                conversation=conversation,
                sender=sender,
                content=content
            )
        except Exception as e:
            logger.error(f"Error saving message: {e}")
            raise

    @database_sync_to_async
    def user_in_conversation(self, user, room_id):
        try:
            chat = PrivateChatRoom.objects.get(id=room_id)
            is_participant = user == chat.participant_1 or user == chat.participant_2
            logger.info(f"User {user.id} in conversation {room_id}: {is_participant}")
            return is_participant
        except PrivateChatRoom.DoesNotExist:
            logger.error(f"PrivateChatRoom with ID {room_id} does not exist for user check")
            return False
        except Exception as e:
            logger.error(f"Error checking user in conversation: {e}")
            return False