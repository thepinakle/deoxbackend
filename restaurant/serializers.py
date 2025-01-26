from rest_framework import serializers
from .models import All_Orders, Restaurant, Products

class AllOrdersSerializer(serializers.ModelSerializer):
    restaurant_name = serializers.CharField(source='restaurant.name', read_only=True)

    class Meta:
        model = All_Orders
        fields = ['id', 'user', 'mobile', 'hostel_name', 'block_number', 'room_number', 'date', 'order_no', 'total', 'delivery_status', 'restaurant_name']

class RestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = ['id', 'name', 'description', 'location', 'picture']

class ProductSerializer(serializers.ModelSerializer):
    restaurant_name = serializers.CharField(source='restaurant.name', read_only=True)
    class Meta:
        model = Products
        fields = [
            'id', 'product_name', 'product_price', 'restaurant_name', 'category', 
            'description', 'product_image', 'carbohydrates', 'proteins', 'fats', 'kilocalories'
        ]

class UpdateDeliveryStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = All_Orders
        fields = ['delivery_status']
