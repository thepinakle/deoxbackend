from django.urls import path
from . import views
from .views import list_orders_by_restaurant
from .views import update_delivery_status

urlpatterns = [
    path('restaurants/', views.restaurant_list, name='restaurant_list'),
    path('api/orders/<str:order_no>/update-delivery-status/', update_delivery_status, name='update-delivery-status'),
    path('restaurants/<str:restaurant_name>/', views.restaurant_detail, name='restaurant_detail'),
    path('cart/add/', views.add_to_cart, name='add_to_cart'),
    path('restaurant-products/<str:restaurant_name>/', views.api_products_by_restaurant_view, name='api_products_by_restaurant'),
    path('order/create/', views.create_order, name='create_order'),
    path('cart/view/', views.view_cart, name='view_cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('orders_by_restaurant/<str:restaurant_name>/', list_orders_by_restaurant, name='orders_by_restaurant'),
    path('api/restaurants/', views.api_restaurant_list, name='api_restaurant_list'),
    path('api/categories/', views.api_categories, name='api_categories'),
    path('api/products/<str:category>/', views.api_products_by_category, name='api_products_by_category'),
    path('api/orders/', views.api_view_orders, name='api_view_orders'),
    path('api/products/', views.api_view_products, name='api_view_products'),
   #  path('api/products/<str:restaurant_name>/', views.api_products_by_restaurant, name='api_products_by_restaurant'),
    # path('api/orders/update-status/<String:order_id>/', views.update_order_delivery_status, name='update_order_delivery_status'),
    # path('api/products/<int:restaurant_id>/', views.api_products_by_restaurant, name='api_products_by_restaurant'),
     # path('api/products/restaurant/<int:restaurant_id>/', views.api_products_by_restaurant_view, name='api_products_by_restaurant'),
      path('cart/delivery-fee/', views.get_delivery_fee, name='get_delivery_fee'),
]