import os
import django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter

# Initialize Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gistconnect.settings')

# Explicitly call django.setup() to ensure all apps are loaded
django.setup()

# Now import after Django is fully initialized
from chat.middleware import JWTAuthMiddlewareStack 
from chat.routing import websocket_urlpatterns

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": JWTAuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})




