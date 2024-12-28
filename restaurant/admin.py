from django.contrib import admin
from .models import Restaurant, Products, Payments, All_Orders, OrderItems, RestaurantOrderView, Cart

@admin.register(Payments)
class PaymentsAdmin(admin.ModelAdmin):
    list_display = ('user', 'mobile', 'amount', 'payments_status', 'mpesa_receipt_number', 'mpesa_transaction_date')
    search_fields = ('user__username', 'mobile', 'mpesa_receipt_number')

@admin.register(All_Orders)
class AllOrdersAdmin(admin.ModelAdmin):
    list_display = ('user', 'mobile', 'hostel_name', 'block_number', 'room_number', 'date', 'order_no', 'total')
    search_fields = ('user__username', 'mobile', 'order_no')

@admin.register(OrderItems)
class OrderItemsAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'price', 'total', 'user', 'delivery_status')
    search_fields = ('order__order_no', 'product__product_name', 'user__username')

class RestaurantOrderViewAdmin(admin.ModelAdmin):
    list_display = ('restaurant', 'order')
    search_fields = ('restaurant__name', 'order__order_no')
    list_filter = ('restaurant',)

class CartAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'price')
    search_fields = ('product__product_name',)
    list_filter = ('product',)

admin.site.register(Restaurant)
admin.site.register(Products)
admin.site.register(RestaurantOrderView, RestaurantOrderViewAdmin)
admin.site.register(Cart, CartAdmin)
