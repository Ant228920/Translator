from django.urls import path
from rest_framework import routers
from django.conf.urls import include

from .views import accept_callback, TranslationCreateView, StatsView, UserViewSet, success_payment, CustomAuthToken, \
    GoogleAuthView, me

router = routers.DefaultRouter()
router.register('users', UserViewSet, basename='user')
router.register(r'stats', StatsView, basename='stats')
router.register(r'translation', TranslationCreateView, basename='translation')

urlpatterns = [
    path('', include(router.urls)),
    path('payment/accept/', accept_callback, name='accept_payment'),
    path('payment/success/', success_payment, name='success_payment'),
    path('auth/', GoogleAuthView.as_view(), name='custom_auth_token'),
    path('auth/me/', me, name='custom_auth_token'),
]