from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt import views as jwt_views
from django.conf import settings

urlpatterns = [
    path(settings.ADMIN_PATH, admin.site.urls),
    path('', include('daseiner.urls')),
    path(r'api-token-auth/', jwt_views.TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path(r'api-token-refresh/', jwt_views.TokenRefreshView.as_view(), name='token_refresh'),
]
