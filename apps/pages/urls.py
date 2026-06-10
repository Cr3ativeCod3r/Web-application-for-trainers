from django.urls import path
from . import views

app_name = 'pages'

urlpatterns = [
    path('o-nas/', views.about_view, name='about'),
    path('kontakt/', views.contact_view, name='contact'),
    path('polityka-prywatnosci/', views.privacy_view, name='privacy'),
]
