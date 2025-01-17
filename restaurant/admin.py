from django.contrib import admin
from .models import Restaurant, Products, Payments, All_Orders, OrderItems, RestaurantOrderView, Cart

@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'description')  # Ensure these fields exist in the Restaurant model
    search_fields = ('name', 'location')

@admin.register(Products)
class ProductsAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'product_price', 'category', 'restaurant')
    search_fields = ('product_name', 'category', 'restaurant__name')

@admin.register(Payments)
class PaymentsAdmin(admin.ModelAdmin):
    list_display = ('user', 'mobile', 'amount', 'payments_status', 'mpesa_receipt_number', 'mpesa_transaction_date')
    search_fields = ('user__username', 'mobile', 'mpesa_receipt_number')

@admin.register(All_Orders)
class AllOrdersAdmin(admin.ModelAdmin):
    list_display = ('user', 'mobile', 'hostel_name', 'block_number', 'room_number', 'date', 'order_no', 'total', 'delivery_status')  # Added delivery_status
    search_fields = ('user__username', 'mobile', 'order_no')

@admin.register(OrderItems)
class OrderItemsAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'price', 'total')
    search_fields = ('order__order_no', 'product__product_name')

@admin.register(RestaurantOrderView)
class RestaurantOrderViewAdmin(admin.ModelAdmin):
    list_display = ('order', 'restaurant', 'status')
    search_fields = ('order__order_no', 'restaurant__name', 'status')

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'quantity', 'price', 'total', 'date_added')
    search_fields = ('user__username', 'product__product_name')
