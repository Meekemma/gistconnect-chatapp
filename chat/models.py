from django.db import models
from django.contrib.auth import get_user_model

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
