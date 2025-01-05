from rest_framework import serializers
from .models import All_Orders

class AllOrdersSerializer(serializers.ModelSerializer):
    restaurant_name = serializers.CharField(source='restaurant.name', read_only=True)

    class Meta:
        model = All_Orders
        fields = ['id', 'user', 'mobile', 'hostel_name', 'block_number', 'room_number', 'date', 'order_no', 'total', 'delivery_status', 'restaurant_name']