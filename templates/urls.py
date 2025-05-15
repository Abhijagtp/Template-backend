# backend/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, TemplateViewSet, ReviewViewSet, PaymentViewSet, payment_webhook, SupportInquiryViewSet

router = DefaultRouter()
router.register(r'templates', TemplateViewSet, basename='templates')
router.register(r'categories', CategoryViewSet, basename='categories')
router.register(r'reviews', ReviewViewSet, basename='reviews')
router.register(r'payments', PaymentViewSet,basename='payments')
router.register(r'support', SupportInquiryViewSet, basename='support')

urlpatterns = [
    path('', include(router.urls)),
    path('webhook/', payment_webhook, name='payment-webhook')
]