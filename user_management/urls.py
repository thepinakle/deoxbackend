from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import UserCreateView, ResetPasswordView, password_reset_confirm, LoginView, DeliveryListView, MarkDeliveryCompleteView, assign_hostels_to_delivery_personnel, hostel_orders

urlpatterns = [
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('create/', UserCreateView.as_view(), name='user_create'),
    path('login/', LoginView.as_view(), name='login'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset_password'),
    path('reset-password-confirm/<uidb64>/<token>/', password_reset_confirm, name='password_reset_confirm'),
    path('deliveries/', DeliveryListView.as_view(), name='delivery_list'),
    path('mark-delivery-complete/<int:pk>/', MarkDeliveryCompleteView.as_view(), name='mark_delivery_complete'),
    path('assign-hostels/', assign_hostels_to_delivery_personnel, name='assign_hostels_to_delivery_personnel'),
    path('hostel-orders/', hostel_orders, name='hostel_orders'),  # New URL pattern
]
