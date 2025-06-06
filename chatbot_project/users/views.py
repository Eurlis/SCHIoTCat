from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import permission_classes

from .serializers import CustomUserSerializer
from .serializers import LoginSerializer


class RegisterAPIView(APIView):
    def post(self, request):
        serializer = CustomUserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "회원가입 성공!"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        return Response({"detail": "이 API는 GET 요청을 지원하지 않습니다."}, status=405)

class LoginAPIView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LogoutAPIView(APIView):
    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"message": "로그아웃 성공"}, status=status.HTTP_200_OK)
        except TokenError:
            return Response({"error": "이미 만료된 토큰입니다."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": "로그아웃 실패", "details": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class UserInfoAPIView(APIView):
    permission_classes = [IsAuthenticated]  # 토큰 필수

    def get(self, request):
        user = request.user  # 토큰에서 인증된 사용자
        return Response({
            "username": user.username,
            "email": user.email,
            "birth_date": user.birth_date
        })