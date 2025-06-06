from .models import CustomUser, UserProfile, Allergy, FoodType
from django.contrib import admin

admin.site.register(CustomUser)
admin.site.register(UserProfile)
admin.site.register(Allergy)
admin.site.register(FoodType)