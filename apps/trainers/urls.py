from django.urls import path
from . import views

app_name = 'trainers'

urlpatterns = [
    path('', views.home_search_view, name='home_search'),
    path('api/autocomplete/', views.autocomplete_view, name='autocomplete'),
    path('aplikuj/', views.apply_trainer_view, name='apply'),
    path('zarzadzaj/', views.admin_dashboard_view, name='admin_dashboard'),
    path('zarzadzaj/zatwierdz/<int:profile_id>/', views.approve_trainer_view, name='approve_trainer'),
    path('zarzadzaj/edycja/zatwierdz/<int:update_id>/', views.approve_update_view, name='approve_update'),
    path('zarzadzaj/edycja/odrzuc/<int:update_id>/', views.reject_update_view, name='reject_update'),
    path('zarzadzaj/podglad/<int:profile_id>/', views.admin_profile_preview_view, name='admin_profile_preview'),
    path('zarzadzaj/edycja/podglad/<int:update_id>/', views.admin_update_preview_view, name='admin_update_preview'),
    path('zarzadzaj/zbanuj/<int:profile_id>/', views.ban_trainer_view, name='ban_trainer'),
    path('zarzadzaj/odwies/<int:profile_id>/', views.unban_trainer_view, name='unban_trainer'),
    path('zarzadzaj/usun/<int:profile_id>/', views.delete_trainer_view, name='delete_trainer'),
    path('zarzadzaj/posty/usun/<int:post_id>/', views.admin_delete_post_view, name='admin_delete_post'),
    path('moje-konto/', views.trainer_account_view, name='account'),
    path('moje-konto/publikacje/', views.post_list_view, name='post_list'),
    path('moje-konto/publikacje/dodaj/', views.post_create_view, name='post_create'),
    path('moje-konto/publikacje/edytuj/<int:post_id>/', views.post_edit_view, name='post_edit'),
    path('moje-konto/publikacje/usun/<int:post_id>/', views.post_delete_view, name='post_delete'),
    path('usun-konto/', views.delete_account_view, name='delete_account'),
    path('<slug:username>/', views.public_profile_view, name='public_profile'),
    path('<slug:username>/<slug:slug>/', views.public_post_view, name='public_post'),
]
