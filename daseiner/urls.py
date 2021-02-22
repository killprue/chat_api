from django.urls import path, include, re_path
from rest_framework import routers
from . import views

router = routers.SimpleRouter(trailing_slash=False)
router.register(r'api/users', views.UserViewSet)

urlpatterns = [
    path(r'api/validate-room/<str:room_code>', views.RoomValidationView.as_view()),
    path(r'api/user-settings/', views.UserSettingsView.as_view()),
    path(r'api/chat-turn/<str:room_id>', views.ChatTurnView.as_view()),
    path(r'api/question/<str:room_id>', views.QuestionView.as_view()),
    path(r'api/check-current-matches/', views.CheckForMatchView.as_view()),
    path('activate/<uidb64>/<token>/', views.ActivateAccount.as_view(), name='activate'),
]
urlpatterns += router.urls
