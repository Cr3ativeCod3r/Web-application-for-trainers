from django.urls import path
from . import views

app_name = 'trainers'

urlpatterns = [
    path('', views.home_search_view, name='home_search'),
    path('api/autocomplete/', views.autocomplete_view, name='autocomplete'),
    path('aplikuj/', views.apply_trainer_view, name='apply'),
    path('moje-konto/', views.trainer_account_view, name='account'),
    path('moje-konto/publikacje/', views.post_list_view, name='post_list'),
    path('moje-konto/publikacje/dodaj/', views.post_create_view, name='post_create'),
    path('moje-konto/publikacje/edytuj/<int:post_id>/', views.post_edit_view, name='post_edit'),
    path('moje-konto/publikacje/usun/<int:post_id>/', views.post_delete_view, name='post_delete'),
    path('usun-konto/', views.delete_account_view, name='delete_account'),
    path('<slug:username>/', views.public_profile_view, name='public_profile'),
    path('<slug:username>/<slug:slug>/', views.public_post_view, name='public_post'),
]
