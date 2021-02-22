from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
import daseiner.routing
from .socketmiddleware import TokenAuthMiddleware

application = ProtocolTypeRouter({
    'websocket': TokenAuthMiddleware(
        URLRouter(
            daseiner.routing.websocket_urlpatterns
        )
    ),
})
