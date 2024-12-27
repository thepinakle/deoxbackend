from django.urls import path
from . import views

urlpatterns = [
    path('order/create/', views.create_order, name='create_order'),
    path('order/mark-delivery-complete/<int:pk>/', views.mark_delivery_complete, name='mark_delivery_complete'),
    path('cart/add/', views.add_to_cart, name='add_to_cart'),
    path('cart/view/', views.view_cart, name='view_cart'),
    path('mpesa/callback/', views.mpesa_callback, name='mpesa_callback'),
]