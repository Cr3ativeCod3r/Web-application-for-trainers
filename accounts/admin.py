from django.contrib import admin
from .models import CustomUser

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('email', 'status', 'is_active', 'is_staff', 'date_joined')
    list_filter = ('status', 'is_active', 'is_staff')
    search_fields = ('email',)
    ordering = ('-date_joined',)
    
    fieldsets = (
        ('Dane logowania', {'fields': ('email', 'password')}),
        ('Status konta', {'fields': ('status', 'is_active')}),
        ('Uprawnienia', {'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Daty', {'fields': ('last_login', 'date_joined')}),
    )
    readonly_fields = ('date_joined', 'last_login')
