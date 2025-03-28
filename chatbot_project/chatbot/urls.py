from django.urls import path
from .views import ChatbotAPIView, RegisterAPIView, LogoutAPIView   # 사용할 View를 가져옵니다.

urlpatterns = [
    path('chat/', ChatbotAPIView.as_view(), name='chatbot'),
    path('register/', RegisterAPIView.as_view(), name='register'),
    path('logout/', LogoutAPIView.as_view(), name='logout'),
]
