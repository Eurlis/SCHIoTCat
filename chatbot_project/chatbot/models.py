from django.db import models

class ChatMessage(models.Model):
    user_message = models.TextField()
    bot_response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user_message

class Food(models.Model):
        name = models.CharField(max_length=100)
        taste = models.CharField(max_length=50)  # 예: '매운', '단맛'
        location = models.CharField(max_length=100)  # 예: '신촌', '강남'
        price = models.IntegerField()  # 단위: 원
        def __str__(self):
            return self.name
