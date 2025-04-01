import openai
import os

from django.contrib.auth.hashers import make_password
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from .models import Food
# 환경 변수에서 OpenAI API 키 불러오기
openai.api_key = os.getenv("OPENAI_API_KEY")


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

            matched_foods = Food.objects.filter(
                name__icontains=user_message
            ) | Food.objects.filter(
                taste__icontains=user_message
            ) | Food.objects.filter(
                location__icontains=user_message
            ) | Food.objects.filter(
                price__icontains=user_message  # 💡 설명까지 체크해도 좋음
            )

            if matched_foods.exists():
                best_food = matched_foods.first()  # 첫 번째 추천 음식
                food_info = f"{best_food.name} (맛: {best_food.taste}, 위치: {best_food.location}, 가격: {best_food.price}원)"

                messages = [
                    {
                        "role": "system",
                        "content": "당신은 음식 추천 챗봇입니다. 아래 음식 정보를 기반으로 사용자에게 추천 설명을 해주세요."
                    },
                    {
                        "role": "user",
                        "content": f"추천 음식: {food_info}"
                    }
                ]
            else:
                messages = [
                    {
                        "role": "system",
                        "content": "음식 데이터가 없기 때문에, 일반적인 음식 하나를 추천해주세요."
                    },
                    {
                        "role": "user",
                        "content": f"{user_message}"
                    }
                ]
            client = openai.OpenAI()
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",  # ✅ GPT-3.5 사용
                messages=messages,
                temperature=0.0
            )
            bot_response = response.choices[0].message.content  # ✅ 응답 형식

            return Response({"response": bot_response}, status=status.HTTP_200_OK)

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
                token.blacklist()  # ✅ 토큰 블랙리스트에 추가 (무효화)

                return Response({"message": "로그아웃되었습니다."}, status=status.HTTP_205_RESET_CONTENT)

            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

