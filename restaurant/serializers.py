from rest_framework import serializers
from .models import All_Orders

class AllOrdersSerializer(serializers.ModelSerializer):
    restaurant_name = serializers.CharField(source='restaurant.name', read_only=True)

    class Meta:
        model = All_Orders
        fields = ['id', 'user', 'mobile', 'hostel_name', 'block_number', 'room_number', 'date', 'order_no', 'total', 'delivery_status', 'restaurant_name']

from rest_framework import serializers
from .models import Restaurant

class RestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = ['id', 'name', 'description', 'location', 'picture']



from .models import Products

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Products
        fields = ['id', 'product_name', 'product_price', 'category', 'description', 'product_image']



from rest_framework import serializers
from .models import All_Orders

class UpdateDeliveryStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = All_Orders
        fields = ['delivery_status']

