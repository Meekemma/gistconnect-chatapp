
from django.db.models.signals import post_save
from django.core.mail import EmailMultiAlternatives
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.conf import settings
from .models import *
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

User = get_user_model()

import logging

logger = logging.getLogger(__name__)




@receiver(post_save, sender=User)
def customer_Profile(sender, instance, created, *args, **kwargs):
    if created:
        # Ensure the necessary groups are created
        free_group, created = Group.objects.get_or_create(name='Free')
        
        # Add the user to the "Free" group by default
        instance.groups.add(free_group)

        UserProfile.objects.create(
            user=instance,
            first_name=instance.first_name,
            last_name=instance.last_name,
            email=instance.email,
        )
        



@receiver(post_save, sender=User)
def update_Profile(sender, instance, created, *args, **kwargs):
    if not created:
        profile, created = UserProfile.objects.get_or_create(user=instance)
        if created:
            print('User Profile was missing and has been created for existing user')
        else:
            profile.save()