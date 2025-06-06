from rest_framework import serializers
from .models import ChatMessage ## Review, Food


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = '__all__'


# class ReviewSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Review
#         fields = ['id', 'food', 'content', 'rating', 'created_at']
#
# class FoodSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Food
#         fields = ['id', 'name']