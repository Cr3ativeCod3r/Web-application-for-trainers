from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('trenerzy/', include('apps.accounts.urls')),
    path('accounts/', include('allauth.urls')),
    path('', include('apps.pages.urls')),
    path('', include('apps.trainers.urls')),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    # Additional path to test 404 view
    from django.views.defaults import page_not_found
    urlpatterns += [
        path('404/', page_not_found, kwargs={'exception': Exception("Test 404")}),
    ]
