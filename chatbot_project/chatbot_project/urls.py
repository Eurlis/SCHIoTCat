from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,  # 로그인 (access, refresh)
    TokenRefreshView,     # access 재발급
)
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('chatbot.urls')),
    path('api/', include('chatbot.urls')),
    path("api/users/", include("users.urls")),
    path('api/users/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/users/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/users/', include('users.urls')),

]
