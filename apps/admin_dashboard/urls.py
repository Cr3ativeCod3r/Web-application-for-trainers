from django.urls import path
from . import views

app_name = 'admin_dashboard'

urlpatterns = [
    path('', views.admin_dashboard_view, name='dashboard'),
    path('zatwierdz/<int:profile_id>/', views.approve_trainer_view, name='approve_trainer'),
    path('edycja/zatwierdz/<int:update_id>/', views.approve_update_view, name='approve_update'),
    path('edycja/odrzuc/<int:update_id>/', views.reject_update_view, name='reject_update'),
    path('podglad/<int:profile_id>/', views.admin_profile_preview_view, name='admin_profile_preview'),
    path('edycja/podglad/<int:update_id>/', views.admin_update_preview_view, name='admin_update_preview'),
    path('zbanuj/<int:profile_id>/', views.ban_trainer_view, name='ban_trainer'),
    path('odwies/<int:profile_id>/', views.unban_trainer_view, name='unban_trainer'),
    path('usun/<int:profile_id>/', views.delete_trainer_view, name='delete_trainer'),
    path('posty/usun/<int:post_id>/', views.admin_delete_post_view, name='admin_delete_post'),
]
