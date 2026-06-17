from django.contrib import admin
from .models import TrainerProfile, TrainerProfileUpdate

# @admin.register(TrainerProfile)
# class TrainerProfileAdmin(admin.ModelAdmin):
#     list_display = ('full_name', 'contact_email', 'sport', 'location', 'hourly_rate', 'created_at')
#     search_fields = ('full_name', 'contact_email', 'sport', 'location', 'user__email')
#     list_filter = ('gender', 'training_type', 'created_at')
#     readonly_fields = ('created_at', 'updated_at')
#     
#     fieldsets = (
#         ('Powiązanie z kontem', {'fields': ('user', 'username')}),
#         ('Podstawowe dane', {'fields': ('full_name', 'sport', 'location', 'headline', 'hourly_rate', 'gender', 'training_type')}),
#         ('Opisy', {'fields': ('description', 'classes_description')}),
#         ('Kontakt', {'fields': ('contact_email', 'contact_phone')}),
#         ('Media społecznościowe', {'fields': ('instagram', 'facebook', 'tiktok')}),
#         ('Zdjęcie', {'fields': ('profile_picture',)}),
#         ('Systemowe', {'fields': ('created_at', 'updated_at')}),
#     )

# @admin.register(TrainerProfileUpdate)
# class TrainerProfileUpdateAdmin(admin.ModelAdmin):
#     list_display = ('profile', 'full_name', 'contact_email', 'created_at')
#     search_fields = ('profile__full_name', 'profile__contact_email', 'full_name', 'contact_email')
#     readonly_fields = ('created_at',)
