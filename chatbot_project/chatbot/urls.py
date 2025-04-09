from django.urls import path
from .views import ChatbotAPIView, RegisterAPIView, LogoutAPIView, ReviewCreateAPIView, \
    ReviewListByFoodAPIView  # 사용할 View를 가져옵니다.

urlpatterns = [
    path('chat/', ChatbotAPIView.as_view(), name='chatbot'),
    path('register/', RegisterAPIView.as_view(), name='register'),
    path('logout/', LogoutAPIView.as_view(), name='logout'),
    path('review/', ReviewCreateAPIView.as_view(), name='review-create'),
    path('review/<int:food_id>/', ReviewListByFoodAPIView.as_view(), name='review-list-by-food'),
]
