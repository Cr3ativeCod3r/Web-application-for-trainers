from django.contrib import admin
from django.contrib.auth.models import Group
from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialApp, SocialToken, SocialAccount
try:
    from django.contrib.sites.models import Site
except ImportError:
    Site = None

from .models import CustomUser, GoogleAccount

# Unregister unnecessary models from the admin panel
admin.site.unregister(Group)

try:
    admin.site.unregister(EmailAddress)
except admin.sites.NotRegistered:
    pass

try:
    admin.site.unregister(SocialApp)
except admin.sites.NotRegistered:
    pass

try:
    admin.site.unregister(SocialToken)
except admin.sites.NotRegistered:
    pass

try:
    admin.site.unregister(SocialAccount)
except admin.sites.NotRegistered:
    pass

if Site:
    try:
        admin.site.unregister(Site)
    except admin.sites.NotRegistered:
        pass

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

@admin.register(GoogleAccount)
class GoogleAccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'provider', 'uid', 'last_login', 'date_joined')
    search_fields = ('user__email', 'uid')
    list_filter = ('provider',)
    
    fieldsets = (
        ('Podstawowe', {'fields': ('user', 'provider', 'uid')}),
        ('Dane dodatkowe', {'fields': ('extra_data',)}),
        ('Daty', {'fields': ('last_login', 'date_joined')}),
    )
    readonly_fields = ('date_joined', 'last_login')
