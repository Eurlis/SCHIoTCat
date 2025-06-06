from django.db import models

class ChatMessage(models.Model):
    user_message = models.TextField()
    bot_response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user_message

from django.db import models

class ReviewCheonanWithLatlng(models.Model):
    store_name = models.TextField(db_column='가게이름', primary_key=True)  # 문자열 PK 지정
    category = models.TextField(db_column='카테고리', blank=True, null=True)
    address = models.TextField(db_column='주소', blank=True, null=True)
    convenience = models.TextField(db_column='편이점', blank=True, null=True)
    contact = models.TextField(db_column='연락처', blank=True, null=True)
    rating = models.BigIntegerField(db_column='평점', blank=True, null=True)
    rating_count = models.BigIntegerField(db_column='평점 건수', blank=True, null=True)
    top_keywords = models.TextField(db_column='상위키워드', blank=True, null=True)
    positive_ratio = models.FloatField(db_column='긍정비율', blank=True, null=True)
    negative_ratio = models.FloatField(db_column='부정비율', blank=True, null=True)
    review_count = models.IntegerField(db_column='리뷰수', blank=True, null=True)
    latitude = models.FloatField(db_column='위도', blank=True, null=True)
    longitude = models.FloatField(db_column='경도', blank=True, null=True)

    class Meta:
        managed = False  # 💥 마이그레이션 없이 DB에 이미 존재하는 테이블
        db_table = 'review_cheonan_with_latlng'
#
#
#
#
#     def __str__(self):
#         return self.name
#
# class Review(models.Model): #DB 리뷰 객체
#     food = models.ForeignKey(Food, on_delete=models.CASCADE, related_name='reviews')
#     content = models.TextField()
#     rating = models.IntegerField()
#     created_at = models.DateTimeField(auto_now_add=True)
#
#     def __str__(self):
#         return f"{self.food.name} - {self.rating}점"
