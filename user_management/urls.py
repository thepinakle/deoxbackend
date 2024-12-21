from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import UserCreateView, ResetPasswordView, password_reset_confirm, LoginView, DeliveryListView, MarkDeliveryCompleteView, AssignHostelsToDeliveryPersonnelView

urlpatterns = [
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('register/', UserCreateView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('password/reset/', ResetPasswordView.as_view(), name='password_reset'),
    path('reset-password/<str:token>/', password_reset_confirm, name='password_reset_confirm'),
    path('deliveries/', DeliveryListView.as_view(), name='delivery_list'),
    path('deliveries/<int:pk>/complete/', MarkDeliveryCompleteView.as_view(), name='mark_delivery_complete'),
    path('assign-hostels/', AssignHostelsToDeliveryPersonnelView.as_view(), name='assign_hostels'),
]
