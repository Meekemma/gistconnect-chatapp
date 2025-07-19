from channels.generic.websocket import AsyncWebsocketConsumer
import json
import logging
from .models import PrivateChatRoom, Message, GroupChatRoom, GroupMember,GroupMessage
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
        








class GroupChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for handling real-time group chat functionality."""

    async def connect(self):
        """Handle WebSocket connection establishment and validate user access."""
        user = self.scope["user"]
        self.room_name = self.scope['url_route']['kwargs']['group_id']
        self.room_group_name = f"group_{self.room_name}"

        # Reject connection if user is not authenticated
        if not user.is_authenticated:
            await self.close()
            return

        # Verify user is a member of the requested group
        is_member = await self.user_in_group(user, self.room_name)
        if not is_member:
            await self.close()
            return

        # Add user to the group channel and accept connection
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        """Remove user from channel group on disconnection."""
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        """Process incoming messages and broadcast to group members."""
        user = self.scope["user"]
        
        # Ensure user is still authenticated
        if not user.is_authenticated:
            return

        try:
            # Parse incoming message data
            data = json.loads(text_data)
            content = data.get('message')
            message_type = data.get('message_type', 'text')
            reply_to_id = data.get('reply_to')

            # Debug logging for troubleshooting
            logger.info(f"Received data: {data}")
            logger.info(f"Reply to ID: {reply_to_id}")

            # Validate group exists
            group = await self.get_group(self.room_name)
            if not group:
                return

            # Fetch reply message if this is a reply
            reply_to = await self.get_reply(reply_to_id) if reply_to_id else None
            logger.info(f"Reply to message found: {reply_to}")
            
            # Save message to database
            msg = await self.save_message(group, user, content, message_type, reply_to)

            # Broadcast message to all group members
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'group_message',
                    'message_id': str(msg.id), 
                    'message': msg.content,
                    'sender_id': str(user.id),
                    'sender_username': user.username,
                    'message_type': msg.message_type,
                    'timestamp': msg.timestamp.isoformat(),
                    'reply_to': await self.format_reply_data(msg.reply_to) if msg.reply_to else None
                }
            )

        except Exception as e:
            logger.error(f"Error in receive: {e}")

    async def group_message(self, event):
        """Send message events to WebSocket client."""
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def format_reply_data(self, reply_message):
        """Format reply message data for client consumption."""
        if not reply_message:
            return None
        
        return {
            "id": str(reply_message.id),
            "content": reply_message.content,
            "sender_username": reply_message.sender.username if reply_message.sender else "Deleted User"
        }

    @database_sync_to_async
    def user_in_group(self, user, group_id):
        """Check if user is a member of the specified group."""
        return GroupMember.objects.filter(group_id=group_id, user=user).exists()

    @database_sync_to_async
    def get_group(self, group_id):
        """Retrieve group chat room by ID."""
        try:
            return GroupChatRoom.objects.get(id=group_id)
        except GroupChatRoom.DoesNotExist:
            return None

    @database_sync_to_async
    def get_reply(self, reply_id):
        """Retrieve message by ID for reply functionality with optimized query."""
        try:
            logger.info(f"Looking for reply message with ID: {reply_id}")
            message = GroupMessage.objects.select_related('sender').get(id=reply_id)
            logger.info(f"Found reply message: {message}")
            return message
        except GroupMessage.DoesNotExist:
            logger.error(f"Reply message with ID {reply_id} not found")
            return None
        except Exception as e:
            logger.error(f"Error getting reply message: {e}")
            return None

    @database_sync_to_async
    def save_message(self, group, user, content, message_type, reply_to=None):
        """Save new message to database with optional reply relationship."""
        logger.info(f"Saving message with reply_to: {reply_to}")
        message = GroupMessage.objects.create(
            group=group,
            sender=user,
            content=content,
            message_type=message_type,
            reply_to=reply_to
        )
        logger.info(f"Message saved: {message}, reply_to: {message.reply_to}")
        return message