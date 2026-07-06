from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('', include('apps.accounts.urls')),
    
    path('accounts/', include('allauth.urls')),
    path('zarzadzaj/', include('apps.admin_dashboard.urls')),
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

    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
