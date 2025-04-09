import openai
import os
from django.db.models import Q
from django.contrib.auth.hashers import make_password
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from .models import Food, Review
from .serializers import ReviewSerializer

# 환경 변수에서 OpenAI API 키 불러오기 (일단 삭제)
# openai.api_key = os.getenv("OPENAI_API_KEY")

TASTE_KEYWORDS = ["구수한", "진한", "달콤한", "담백한", "매운", "단맛", "매콤한"]


class ChatbotAPIView(APIView):
    def post(self, request):
        if not request.content_type == "application/json":
            return Response({"error": "Content-Type을 application/json으로 설정하세요."}, status=status.HTTP_400_BAD_REQUEST)

        if not request.data:
            return Response({"error": "JSON 데이터를 포함하여 요청하세요."}, status=status.HTTP_400_BAD_REQUEST)

        user_message = request.data.get("message")

        if not user_message:
            return Response({"error": "메시지를 입력하세요."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # user_message에서 맛 키워드를 추출
            matched_keywords = [taste for taste in TASTE_KEYWORDS if taste in user_message]

            if matched_keywords:
                matched_foods = Food.objects.filter(taste__in=matched_keywords)
            else:
                matched_foods = Food.objects.none()

            if matched_foods.exists():
                # 추천 결과 리스트 형태로 응답
                food_info = [
                    f"{food.name} (맛: {food.taste}, 위치: {food.location}, 가격: {food.price}원)"
                    for food in matched_foods
                ]
                return Response({"response": food_info}, status=status.HTTP_200_OK)
            else:
                return Response({"response": "조건에 맞는 음식이 없습니다. 다른 키워드로 다시 시도해주세요!"},
                                status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RegisterAPIView(APIView):
    permission_classes = [AllowAny]  # 누구나 접근 가능

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        if not username or not password:
            return Response({"error": "아이디와 비밀번호를 입력하세요."}, status=status.HTTP_400_BAD_REQUEST)

        # 중복 계정 방지
        if User.objects.filter(username=username).exists():
            return Response({"error": "이미 존재하는 사용자입니다."}, status=status.HTTP_400_BAD_REQUEST)

        # 사용자 생성
        user = User.objects.create(username=username, password=make_password(password))

        # JWT 토큰 발급
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        return Response({
            "message": "회원가입이 완료되었습니다.",
            "access_token": access_token,
            "refresh_token": str(refresh)
        }, status=status.HTTP_201_CREATED)

class LogoutAPIView(APIView):
        def post(self, request):
            try:
                refresh_token = request.data.get("refresh")
                if not refresh_token:
                    return Response({"error": "리프레시 토큰이 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)

                token = RefreshToken(refresh_token)
                token.blacklist()  # 토큰 블랙리스트에 추가 (무효화)

                return Response({"message": "로그아웃되었습니다."}, status=status.HTTP_205_RESET_CONTENT)

            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ReviewCreateAPIView(APIView):
    def post(self, request):
        serializer = ReviewSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "리뷰가 등록되었습니다.", "review": serializer.data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ReviewListByFoodAPIView(ListAPIView):
    serializer_class = ReviewSerializer

    def get_queryset(self):
        food_id = self.kwargs['food_id']
        return Review.objects.filter(food_id=food_id).order_by('-created_at')