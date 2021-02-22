from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/participant-chat/(?P<room_name>.*)/$', consumers.ParticipantChatConsumer),
    re_path(r'ws/participant-match/(?P<room_name>.*)/$', consumers.ParticipantMatchingConsumer),
    re_path(r'ws/judge-chat/(?P<room_name>.*)/$', consumers.JudgeChatConsumer),
    re_path(r'ws/judge-match/(?P<room_name>.*)/$', consumers.JudgeMatchingConsumer),
]
