from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import permission_classes

from .serializers import CustomUserSerializer, LocationSerializer
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

class UpdateLocationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        # 1) Serializer를 사용해 요청 데이터 검증
        serializer = LocationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "latitude와 longitude를 float 형태로 보내주세요.", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2) 검증된 데이터에서 위도, 경도 꺼내기
        latitude = serializer.validated_data['latitude']
        longitude = serializer.validated_data['longitude']

        try:
            # 3) 사용자 모델 필드 업데이트
            user.latitude = latitude
            user.longitude = longitude
            user.save(update_fields=['latitude', 'longitude'])

            return Response(
                {"status": "위치 정보가 업데이트되었습니다."},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"error": f"저장 중 오류가 발생했습니다: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )