from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    birth_date = models.DateField(blank=True, null=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    def __str__(self):
        return self.username

class Allergy(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class FoodType(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
    allergies = models.ManyToManyField(Allergy, blank=True)
    food_types = models.ManyToManyField(FoodType, blank=True)

    def __str__(self):
        return f"{self.user.username}'s profile"
