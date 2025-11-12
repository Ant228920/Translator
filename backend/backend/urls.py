from django.contrib import admin
from django.urls import path
from django.conf.urls import include
from rest_framework.authtoken.views import obtain_auth_token

from api.views import CustomAuthToken

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('auth/', CustomAuthToken.as_view(), name='custom_auth_token'),
]
