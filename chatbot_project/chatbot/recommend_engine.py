# chatbot/recommend_engine.py

import os, pickle
from math import radians, sin, cos, sqrt, atan2

from django.db.models import Q
from sklearn.metrics.pairwise import cosine_similarity

from .models import ReviewCheonanWithLatlng

# 1) TF-IDF 벡터라이저 로드
BASE_DIR = os.path.dirname(__file__)
with open(os.path.join(BASE_DIR, "tfidf.pkl"), "rb") as f:
    TFIDF = pickle.load(f)

# 2) 사전 키워드 매핑
KW_MAP = {
    "스시":  ["스시", "초밥", "일식", "롤", "초밥뷔페"],
    "고기":  ["고기", "소고기구이", "육류", "고기요리", "돼지고기구이", "정육식당", "오리요리", "스테이크", "립", "닭갈비","족발",
                                      "보쌈", "양꼬치", "고기뷔페", "양갈비"],

    "한식": ["쌈밥", "두부요리", "한정식", "닭갈비", "칼국수", "만두", "이북음식", "냉면", "감자탕", "국수", "국밥", "칼국수",
                                      "만두", "순대", "순댓국", "보리밥", "막국수", "주꾸미 요리", "장어" ,"먹장어요리", "해장국",
                                     "전", "빈대떡", "찌개", "전골", "백숙", "삼계탕", "족발", "보쌈", "매운탕", "해물탕"],

    "야식": ["닭발", "요리주점", "주꾸미요리", "닭갈비","족발","곱창", "막창", "양",
                                      "보쌈", "양꼬치"],
    "해산물": ["먹장어요리","주꾸미 요리", "장어", "생선회","매운탕", "해물탕", "게요리", "오징어"],

    "양식": ["양식","이탈리아음식", "스파게티", "파스타전문"," 스테이크", "립", "피자"],

    "중식": ["중식당","짬뽕", "짜장", "탕수육"],

    "일식": ["일본식라면","우동", "소바", "일식당"],

    "분식": ["종합분식","분식"],

    # … 필요시 추가 …
}

def _haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return 2 * R * atan2(sqrt(a), sqrt(1 - a))


def recommend(keyword: str,
              u_lat: float, u_lon: float,
              location_filter: str = "",      # ← 추가된 매개변수
              alpha: float = 0.7, beta: float = 0.3,
              top_k: int = 10, radius_km: float = 20.0):
    """
    • keyword         : 카테고리 키워드
    • location_filter : 사용자 메시지에서 추출된 장소명 (빈 문자열이면 무시)
    """

    # 1) 키워드 확장
    mapped = KW_MAP.get(keyword, [keyword])

    # 2) DB 후보 조회
    q = Q()
    for m in mapped:
        q |= Q(top_keywords__icontains=m) | Q(category__icontains=m)

    # location_filter 가 있으면 주소에도 포함 조건 추가
    if location_filter:
        q &= Q(address__icontains=location_filter)

    qs = ReviewCheonanWithLatlng.objects.filter(q).values(
        "store_name", "address", "rating", "review_count",
        "latitude", "longitude",
        "top_keywords", "convenience", "category"
    )
    candidates = list(qs)
    if not candidates:
        return []

    # 3) combined_features 생성
    docs = []
    for c in candidates:
        parts = [c.get(fld) or "" for fld in ("top_keywords", "convenience", "category")]
        docs.append(" ".join(parts))

    # 4) TF-IDF 유사도 계산
    query_vec = TFIDF.transform([" ".join(mapped)])
    cand_vec  = TFIDF.transform(docs)
    sim_scores = cosine_similarity(query_vec, cand_vec)[0]

    # 5) 거리 점수 계산
    dist_scores = []
    for c in candidates:
        d = _haversine(u_lat, u_lon, c["latitude"], c["longitude"])
        dist_scores.append(max(0.0, 1 - d / radius_km))

    # 6) 가중합 & 정렬
    scored = [(alpha * sim_scores[i] + beta * dist_scores[i], c)
              for i, c in enumerate(candidates)]
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:top_k]

    # (디버그 로그)
    print("🔍 키워드:", mapped, "| 장소 필터:", location_filter)
    print("🔍 유사도 예시:", sim_scores[:5])
    print("🔍 거리 예시  :", dist_scores[:5])
    print("🔍 합산 예시:", [round(s,3) for s,_ in scored][:5])

    # 7) 튜플 형태 반환
    results = []
    for _, c in top:
        results.append((
            c["store_name"],
            c["address"],
            c["rating"],
            c["review_count"],
            c["latitude"],
            c["longitude"],
        ))
    return results
