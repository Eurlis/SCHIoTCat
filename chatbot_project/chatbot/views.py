import ast
import os
import requests
from dotenv import load_dotenv

from langchain_community.utilities.sql_database import SQLDatabase
from langchain_openai import ChatOpenAI
from langchain.chains import create_sql_query_chain
from langchain.prompts import PromptTemplate

import traceback

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django.core.cache import cache

load_dotenv()

# (기존 SQL 프롬프트 – 음식점 일반 추천용)
sql_prompt = PromptTemplate.from_template("""
너는 SQL 쿼리를 생성하는 전문가야.
반드시 아래 항목을 포함해서 쿼리를 생성해:

- `가게이름`, `주소`, `평점`, `리뷰수`, `위도`, `경도`
- FROM review_cheonan_with_latlng
- `연락처`, `편이점`, `평점 건수`, `상위키워드`, `긍정비율`, `부정비율` 은 포함하지 말 것
주의: WHERE 절에서 `상위키워드`는 절대 사용하지 말 것!
테이블 정보:
{table_info}

사용자 질문: {input}

쿼리 결과는 최대 {top_k}개로 제한하고, SQL만 출력해.
""")


class LangChainChatAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        user_message = request.data.get("message")

        if not user_message:
            return Response({"error": "메시지를 입력하세요."}, status=status.HTTP_400_BAD_REQUEST)

        greetings = ["안녕", "ㅎㅇ", "반가워", "안녕하세요", "하이", "hello", "hi"]
        if any(greet in user_message.lower() for greet in greetings):
            return Response({
                "response": "안녕하세요! 😊 저는 음식점 추천 챗봇입니다.\n맛집을 찾고 계신가요? 궁금한 지역이나 조건을 말씀해주세요!"
            })

        # === 날씨 기반 추천 ===
        if "날씨" in user_message:
            try:
                # 1) 주소 → 위도/경도 변환
                address = "천안시 서북구"  # 예시 주소 (필요하면 사용자 위치로 변경)
                geo_url = "https://nominatim.openstreetmap.org/search"
                geo_params = {
                    'q': address,
                    'format': 'json',
                    'limit': 1
                }
                geo_res = requests.get(
                    geo_url,
                    params=geo_params,
                    headers={'User-Agent': 'weather-app'}
                )
                # 주소 변환 실패 체크
                if geo_res.status_code != 200 or not geo_res.json():
                    return Response({"response": "주소를 찾을 수 없습니다."})

                geo_data = geo_res.json()[0]
                lat = geo_data.get('lat')
                lon = geo_data.get('lon')

                # 2) OpenWeatherMap 날씨 조회
                API_KEY = os.getenv("OPENWEATHER_API_KEY")
                weather_url = "https://api.openweathermap.org/data/2.5/weather"
                weather_params = {
                    'lat': lat,
                    'lon': lon,
                    'appid': API_KEY,
                    'units': 'metric',
                    'lang': 'kr'
                }
                weather_res = requests.get(weather_url, params=weather_params)

                # 날씨 API 호출 실패 체크
                if weather_res.status_code != 200:
                    print(f"❌ OpenWeatherMap API 응답 실패: status_code={weather_res.status_code}, body={weather_res.text}")
                    return Response({"response": "날씨 정보를 불러올 수 없습니다."}, status=status.HTTP_502_BAD_GATEWAY)

                weather_data = weather_res.json()
                # 'weather' 키 유무 체크
                if 'weather' not in weather_data or not weather_data['weather']:
                    print("❌ OpenWeatherMap 응답에 'weather' 정보가 없습니다:", weather_data)
                    return Response({"response": "날씨 정보를 불러올 수 없습니다."}, status=status.HTTP_502_BAD_GATEWAY)

                main_weather = weather_data['weather'][0].get('main', '').lower()
                description = weather_data['weather'][0].get('description', '')
                temp = weather_data.get('main', {}).get('temp')
                feels_like = weather_data.get('main', {}).get('feels_like')

                # 필수 정보가 없을 경우
                if temp is None or feels_like is None:
                    print("❌ OpenWeatherMap 응답에 온도 정보가 부족합니다:", weather_data)
                    return Response({"response": "날씨 정보를 불러올 수 없습니다."}, status=status.HTTP_502_BAD_GATEWAY)

                # 3) 날씨 기반 추천 키워드 매핑
                if main_weather == "clear":
                    keyword = "냉면"
                elif main_weather == "rain":
                    keyword = "파전"
                elif main_weather == "snow":
                    keyword = "국밥"
                elif main_weather == "clouds":
                    keyword = "파스타"
                else:
                    keyword = "해산물"

                # 4) 날씨 정보 텍스트 구성
                weather_text = (
                    f"🌤️ 현재 {address}의 날씨는 '{description}'이고, "
                    f"기온은 {temp}℃ (체감온도 {feels_like}℃)입니다.\n"
                    f"오늘 같은 날씨에는 보통 '{keyword}'가 생각나네요."
                )

                # 5) 날씨 키워드로 DB에서 맛집 조회
                result_list = []
                try:
                    db = SQLDatabase.from_uri(
                        f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
                        f"@localhost:3306/{os.getenv('DB_NAME')}",
                        include_tables=["review_cheonan_with_latlng"]
                    )
                    # 예시 쿼리: 상위키워드 컬럼에 keyword가 포함된 레코드 3개 추출
                    raw_query = (
                        "SELECT 가게이름, 주소, 평점, 리뷰수, 위도, 경도 "
                        "FROM review_cheonan_with_latlng "
                        f"WHERE 상위키워드 LIKE '%{keyword}%' "
                        "LIMIT 3;"
                    )
                    raw_result = db.run(raw_query)

                    # 결과 파싱
                    if isinstance(raw_result, str) and raw_result.strip().startswith("["):
                        result_list = ast.literal_eval(raw_result)
                    elif isinstance(raw_result, list):
                        result_list = raw_result
                    else:
                        result_list = []
                except Exception as db_err:
                    print("❌ 날씨 기반 DB 조회 오류:\n", traceback.format_exc())
                    result_list = []

                # 6) 캐시에 저장 (일반 추천과 동일하게 동일한 키를 사용)
                #    -> GetRestaurantLocationAPIView에서 동일한 키로 꺼낼 수 있도록
                cache.set(f"recommend_user_{user.id}", result_list[:3], timeout=300)
                print("✅ 날씨 추천 결과 캐시 저장 완료:", result_list[:3])

                # 7) 맛집 리스트 메시지 구성
                if result_list:
                    lines = ["\n오늘 추천 맛집 리스트입니다:"]
                    for idx, item in enumerate(result_list[:3], start=1):
                        if len(item) < 6:
                            continue
                        name, addr, rating, review_count, lat_r, lon_r = item
                        line = (
                            f"{idx}. {name} ({rating}점 ⭐) - {addr} "
                            f"({review_count}개 리뷰)\n"
                        )
                        lines.append(line)
                    db_text = "\n\n".join(lines)
                else:
                    db_text = "\n조건에 맞는 맛집을 찾지 못했습니다. 다른 키워드로 시도해보세요."

                # 8) 최종 응답 결합 후 반환
                return Response({"response": weather_text + db_text})

            except Exception as werr:
                print("❌ 날씨 처리 중 예외 발생:\n", traceback.format_exc())
                return Response({"error": "날씨 정보를 처리하던 중 오류가 발생했습니다."}, status=500)

        # === 일반 음식점 추천 (LangChain + ChatGPT) ===
        try:
            db = SQLDatabase.from_uri(
                f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
                f"@localhost:3306/{os.getenv('DB_NAME')}",
                include_tables=["review_cheonan_with_latlng"]
            )
            llm = ChatOpenAI(temperature=0, api_key=os.getenv("OPENAI_API_KEY"))
            chain = create_sql_query_chain(llm=llm, db=db, prompt=sql_prompt)

            query = chain.invoke({
                "question": user_message,
                "table_info": db.get_table_info(),
                "top_k": 5
            })

            print("📦 생성된 쿼리:", query)
            query = query.strip().strip("```").strip()
            raw_result = db.run(query)
            print("📦 원시 결과:", raw_result)

            # 결과 파싱
            try:
                if raw_result.strip().startswith("["):
                    result_list = ast.literal_eval(raw_result)
                else:
                    result_list = [(raw_result,)]
            except Exception as pe:
                print("❌ 파싱 실패:", pe)
                return Response({"error": "결과 파싱 실패: " + str(pe)}, status=500)

            # 위도/경도 누락 체크
            for item in result_list:
                if len(item) < 6:
                    print("❗ 위도/경도 누락:", item)

            # 9) 캐시에 저장
            cache.set(f"recommend_user_{user.id}", result_list[:3], timeout=300)
            print("✅ 일반 추천 결과 캐시 저장 완료:", result_list[:3])

            if not result_list:
                return Response({"response": "조건에 맞는 맛집이 아직 없어요 😥\n다른 지역이나 조건으로 다시 추천해드릴까요?"})

            answer_lines = []
            for i, item in enumerate(result_list[:3]):
                name, address, rating, review_count = item[:4]
                line = f"{i + 1}. {name} ({rating}점 ⭐) - {address}"
                if review_count:
                    line += f" ({review_count}개 리뷰)"
                answer_lines.append(line)

            response_text = (
                "😋 추천드리는 맛집입니다!\n\n" +
                "\n".join(answer_lines) +
                "\n\n더 많은 맛집을 보고 싶으시면 '더 추천해줘' 라고 입력해보세요!"
            )

            return Response({
                "query": query,
                "response": response_text
            })

        except Exception as e:
            print("❌ 오류 발생:\n", traceback.format_exc())
            return Response({"error": str(e)}, status=500)


class GetRestaurantLocationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        selected_number = request.data.get("number")
        user = request.user

        # 10) 캐시에서 저장된 추천 결과(일반 또는 날씨)를 가져옴
        recent_list = cache.get(f"recommend_user_{user.id}")
        print("📌 캐시에서 불러온 추천 목록:", recent_list)

        if not recent_list:
            return Response({"error": "먼저 추천을 받아주세요."}, status=400)

        if selected_number is None or selected_number > len(recent_list) or selected_number < 1:
            return Response({"error": "유효하지 않은 번호입니다."}, status=400)

        selected = recent_list[selected_number - 1]

        if len(selected) < 6:
            return Response({"error": "위치 정보가 부족합니다."}, status=500)

        # 11) 선택된 맛집의 위도/경도를 돌려줌
        return Response({
            "name": selected[0],
            "address": selected[1],
            "rating": selected[2],
            "review_count": selected[3],
            "latitude": float(selected[4]),
            "longitude": float(selected[5]),
        })
