from django.urls import path
from .views import RegisterAPIView
from .views import LoginAPIView
from .views import LogoutAPIView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('register/', RegisterAPIView.as_view(), name='register'),
    path('login/', LoginAPIView.as_view(), name='login'),
    path('logout/', LogoutAPIView.as_view(), name='logout'),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
