from django.urls import path
from .views import LangChainChatAPIView
from .views import GetRestaurantLocationAPIView
#FoodListAPIView, LangChainChatAPIView, ReviewCreateAPIView,
    # ReviewListByFoodAPIView  # 사용할 View를 가져옵니다.

urlpatterns = [
    path('langchain/', LangChainChatAPIView.as_view(), name='langchain_chat'),
    path('api/get-location/', GetRestaurantLocationAPIView.as_view(), name='get-location'),
    # path('review/', ReviewCreateAPIView.as_view(), name='review-create'),
    # path('foods/<int:food_id>/reviews/', ReviewListByFoodAPIView.as_view(), name='review-list-by-food'),
    # path('foods/', FoodListAPIView.as_view(), name='food-list'),
]
