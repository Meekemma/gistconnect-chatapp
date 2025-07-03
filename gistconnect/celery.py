from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gistconnect.settings')

app = Celery('gistconnect')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

# Optional: add your scheduled tasks here
app.conf.beat_schedule = {
    # "task-name": {
    #     "task": "app.tasks.example_task",
    #     "schedule": crontab(minute="0", hour="*/6"),  # Every 6 hours
    # },
}
