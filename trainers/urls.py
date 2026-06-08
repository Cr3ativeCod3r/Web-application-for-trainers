from django.urls import path
from . import views

app_name = 'trainers'

urlpatterns = [
    path('', views.home_search_view, name='home_search'),
]
