from django.urls import path
from . import views

app_name = 'pages'

urlpatterns = [
    path('o-nas/', views.about_view, name='about'),
    path('kontakt/', views.contact_view, name='contact'),
    path('polityka-prywatnosci/', views.privacy_view, name='privacy'),
    path('quiz/', views.quiz_view, name='quiz'),
    path('quiz/submit/', views.quiz_submit_api, name='quiz_submit'),
    path('strefa-wiedzy/', views.knowledge_base_view, name='knowledge_base'),
]
