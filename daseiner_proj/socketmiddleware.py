from django.db import close_old_connections
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from jwt import decode as jwt_decode
from django.conf import settings
from django.contrib.auth.models import User
from urllib.parse import parse_qs
from channels.db import database_sync_to_async


class TokenAuthMiddleware:
    """
    Custom token auth middleware
    """

    def __init__(self, inner):
        # Store the ASGI application we were passed
        self.inner = inner

    def __call__(self, scope):
        user = None
        database_sync_to_async(close_old_connections)()
        parsed_qs = parse_qs(scope["query_string"].decode("utf8"))
        if parsed_qs:
            token = parsed_qs["token"][0]
            try:
                UntypedToken(token)
            except (InvalidToken, TokenError) as e:
                return self.inner(dict(scope, user=user))
            else:
                decoded_data = jwt_decode(token, settings.SECRET_KEY, algorithms=["HS256"])
                user =  database_sync_to_async(User.objects.get)(
                    id=decoded_data["user_id"]
                )
        return self.inner(dict(scope, user=user))

TokenAuthMiddlewareStack = lambda inner: TokenAuthMiddleware(TokenAuthMiddleware(inner))
