from django.db import models

class ChatMessage(models.Model):
    user_message = models.TextField()
    bot_response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user_message

class Food(models.Model): # DB 음식 객체
        name = models.CharField(max_length=100)
        taste = models.CharField(max_length=50)
        location = models.CharField(max_length=100)
        price = models.IntegerField()
        def __str__(self):
            return self.name

class Review(models.Model): #DB 리뷰 객체
    food = models.ForeignKey(Food, on_delete=models.CASCADE, related_name='reviews')
    content = models.TextField()
    rating = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.food.name} - {self.rating}점"
