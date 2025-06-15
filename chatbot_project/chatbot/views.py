# views.py  ───────────────────────────────────────────────────────────
import ast, os, traceback, requests
from dotenv import load_dotenv
from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.schema import StrOutputParser         # ✅ 새 API
from langchain.schema.runnable import RunnableSequence

from langchain_community.utilities.sql_database import SQLDatabase

from chatbot.recommend_engine import _haversine, recommend

load_dotenv()

# ────────────────── 1. GPT 키워드 추출용 프롬프트 ──────────────────
KEY_PROMPT = PromptTemplate.from_template(r"""
너는 음식점 추천을 위해 사용자의 **음식 종류**와 **장소**를 추출하는 봇이야.
메시지에서 아래 JSON 키 두 가지만 반환해.
  • category: 음식 종류 (예: "카페", "스시", "한식")
  • location: 장소 (예: "신불당", "두정동")
없으면 빈 문자열("").
예) {{"category":"카페","location":"신불당"}}   # ← 중괄호 두 번!
사용자: {input}
""")

# Runnable 파이프라인(Deprecation 없앰)
LLM_PIPE = (
    KEY_PROMPT
    | ChatOpenAI(
        temperature=0,
        model_name="gpt-3.5-turbo",
        api_key=os.getenv("OPENAI_API_KEY"),
      )
    | StrOutputParser()
)

# ───────────────────────── 2. API ─────────────────────────
class LangChainChatAPIView(APIView):
    permission_classes = [IsAuthenticated]

    # ───── POST /api/langchain/ ─────
    def post(self, request):
        user         = request.user
        user_message = request.data.get("message", "").strip()

        if not user_message:
            return Response({"error": "메시지를 입력하세요."},
                            status=status.HTTP_400_BAD_REQUEST)

        # (1) 간단 인사 응대
        if any(greet in user_message.lower() for greet in
               ["안녕", "ㅎㅇ", "반가워", "안녕하세요", "하이", "hello", "hi"]):
            return Response({"response": "안녕하세요! 😊 맛집을 찾고 계신가요?"})

        # (2) 날씨 키워드가 들어오면 별도 로직
        if "날씨" in user_message:
            return self._handle_weather(user)

        # (3) 일반 음식점 추천
        return self._handle_recommend(user, user_message)

    # ───────────── 날씨 추천 분기 ─────────────
    def _handle_weather(self, user):
        try:
            address = "천안시 서북구"
            lat, lon = self._geocode(address)
            weather  = self._fetch_weather(lat, lon)

            keyword_map = {
                "clear":  "냉면",
                "rain":   "파전",
                "snow":   "국밥",
                "clouds": "파스타",
            }
            keyword = keyword_map.get(weather["main"], "해산물")

            weather_text = (
                f"🌤️ 현재 {address}의 날씨는 '{weather['desc']}'이며 "
                f"{weather['temp']}℃ (체감 {weather['feels']}℃)입니다.\n"
                f"오늘 같은 날씨엔 '{keyword}'가 잘 어울려요!"
            )

            result_list = self._query_by_keyword(keyword)
            cache_key   = f"weather_recommend_{user.id}"   # ✅ 캐시 키 분리
            cache.set(cache_key, result_list[:3], 300)

            if not result_list:
                return Response({"response": weather_text +
                                 "\n조건에 맞는 맛집을 찾지 못했습니다."})

            lines = [
                f"{i}. {n} ({r}점⭐) - {a} ({c}개 리뷰)"
                for i, (n, a, r, c, *_)
                in enumerate(result_list[:3], 1)
            ]
            return Response({"response": weather_text + "\n\n" + "\n".join(lines)})

        except Exception:
            traceback.print_exc()
            return Response({"error": "날씨 추천 중 오류 발생."}, status=500)

    # ───────────── 일반 추천 분기 ─────────────
    def _handle_recommend(self, user, user_message):
        try:
            # 1) GPT로 category/location 추출
            kw_json = LLM_PIPE.invoke({"input": user_message})
            parsed = ast.literal_eval(kw_json)
            category  = parsed.get("category", user_message)
            location  = parsed.get("location", "").strip()
            print("🛠 GPT 추출:", parsed)

            # 2) 사용자 좌표 확인
            if user.latitude is None or user.longitude is None:
                return Response({"error": "먼저 내 위치를 등록해주세요."}, status=400)
            u_lat, u_lon = user.latitude, user.longitude

            # 3) 추천 엔진 호출
            results = recommend(
                keyword=category,
                u_lat=u_lat, u_lon=u_lon,
                top_k=5,
                location_filter=location
            )
            if not results:
                return Response({"response": "조건에 맞는 맛집이 없어요 😥"})

            # 4) 캐시 저장
            cache_key = f"user_recommend_{user.id}"        # ✅ 캐시 키 분리
            cache.set(cache_key, results[:3], 300)

            # 5) 응답 메시지
            lines = [
                f"{i}. {n} ({_haversine(u_lat, u_lon, la, lo):.1f}km) - {a}"
                for i, (n, a, *_ , la, lo) in enumerate(results[:3], 1)
            ]
            return Response({"response": "😋 추천 맛집입니다!\n\n" + "\n".join(lines)})

        except Exception:
            traceback.print_exc()
            return Response({"error": "추천 중 오류 발생."}, status=500)

    # ───────────── 헬퍼: 주소→좌표 ─────────────
    def _geocode(self, address):
        res = requests.get("https://nominatim.openstreetmap.org/search",
                           params={"q": address, "format": "json", "limit": 1},
                           headers={"User-Agent": "weather-app"})
        res.raise_for_status()
        j = res.json()[0]
        return j["lat"], j["lon"]

    # ───────────── 헬퍼: 날씨 조회 ─────────────
    def _fetch_weather(self, lat, lon):
        api_key = os.getenv("OPENWEATHER_API_KEY")
        res = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"lat": lat, "lon": lon, "appid": api_key,
                    "units": "metric", "lang": "kr"})
        res.raise_for_status()
        j = res.json()
        return {
            "main":  j["weather"][0]["main"].lower(),
            "desc":  j["weather"][0]["description"],
            "temp":  j["main"]["temp"],
            "feels": j["main"]["feels_like"],
        }

    # ───────────── 헬퍼: 키워드로 3개 조회 ─────────────
    def _query_by_keyword(self, keyword):
        try:
            db = SQLDatabase.from_uri(
                f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
                f"@localhost:3306/{os.getenv('DB_NAME')}",
                include_tables=["review_cheonan_with_latlng"])
            raw = db.run(
                "SELECT 가게이름, 주소, 평점, 리뷰수, 위도, 경도 "
                "FROM review_cheonan_with_latlng "
                f"WHERE 상위키워드 LIKE '%{keyword}%' LIMIT 3")
            return ast.literal_eval(raw) if isinstance(raw, str) else raw
        except Exception:
            traceback.print_exc()
            return []

# ────────────────── 3. 위치 조회 API (캐시 키 수정) ──────────────────
class GetRestaurantLocationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        idx  = request.data.get("number")
        user = request.user

        recent = (cache.get(f"user_recommend_{user.id}") or
                  cache.get(f"weather_recommend_{user.id}"))
        print("📌 캐시 추천:", recent)

        if not recent:
            return Response({"error": "먼저 추천을 받아주세요."}, status=400)
        if not idx or idx < 1 or idx > len(recent):
            return Response({"error": "유효하지 않은 번호입니다."}, status=400)

        n, addr, rate, cnt, lat, lon = recent[idx - 1]
        return Response({
            "name": n, "address": addr,
            "rating": rate, "review_count": cnt,
            "latitude": float(lat), "longitude": float(lon),
        })
