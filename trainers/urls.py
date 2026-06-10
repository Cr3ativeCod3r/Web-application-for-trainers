from django.urls import path
from . import views

app_name = 'trainers'

urlpatterns = [
    path('', views.home_search_view, name='home_search'),
    path('aplikuj/', views.apply_trainer_view, name='apply'),
    path('zarzadzaj/', views.admin_dashboard_view, name='admin_dashboard'),
    path('zarzadzaj/zatwierdz/<int:profile_id>/', views.approve_trainer_view, name='approve_trainer'),
    path('zarzadzaj/edycja/zatwierdz/<int:update_id>/', views.approve_update_view, name='approve_update'),
    path('zarzadzaj/edycja/odrzuc/<int:update_id>/', views.reject_update_view, name='reject_update'),
    path('zarzadzaj/podglad/<int:profile_id>/', views.admin_profile_preview_view, name='admin_profile_preview'),
    path('zarzadzaj/edycja/podglad/<int:update_id>/', views.admin_update_preview_view, name='admin_update_preview'),
    path('moje-konto/', views.trainer_account_view, name='account'),
    path('usun-konto/', views.delete_account_view, name='delete_account'),
    path('<slug:username>/', views.public_profile_view, name='public_profile'),
]
