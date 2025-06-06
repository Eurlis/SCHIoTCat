from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import CustomUser, UserProfile
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Allergy, FoodType
User = get_user_model()

class CustomUserSerializer(serializers.ModelSerializer):
    allergies = serializers.ListField(write_only=True)
    food_types = serializers.ListField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ['username', 'password', 'phone_number', 'birth_date', 'allergies', 'food_types']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        allergy_ids = validated_data.pop('allergies')
        food_type_ids = validated_data.pop('food_types')

        user = CustomUser.objects.create_user(**validated_data)
        profile = UserProfile.objects.create(user=user)

        profile.allergies.set(Allergy.objects.filter(id__in=allergy_ids))
        profile.food_types.set(FoodType.objects.filter(id__in=food_type_ids))
        return user

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(username=data['username'], password=data['password'])
        if user is None:
            raise serializers.ValidationError("아이디 또는 비밀번호가 틀렸습니다.")
        refresh = RefreshToken.for_user(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }