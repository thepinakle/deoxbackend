from django.urls import path
from . import views
from .views import list_orders_by_restaurant

urlpatterns = [
    path('restaurants/', views.restaurant_list, name='restaurant_list'),
    path('restaurants/<int:restaurant_id>/', views.restaurant_detail, name='restaurant_detail'),
    path('cart/add/', views.add_to_cart, name='add_to_cart'),
    path('order/create/', views.create_order, name='create_order'),
    path('cart/view/', views.view_cart, name='view_cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('orders_by_restaurant/<str:restaurant_name>/', list_orders_by_restaurant, name='orders_by_restaurant'),
]