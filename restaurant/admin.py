from django.contrib import admin
from .models import Restaurant, Products, Payments, All_Orders, OrderItems, RestaurantOrderView, Cart

class AllOrdersAdmin(admin.ModelAdmin):
    list_display = ('order_no', 'user', 'total', 'hostel_name', 'block_number', 'room_number', 'date')
    search_fields = ('order_no', 'user__username', 'hostel_name', 'block_number', 'room_number')
    list_filter = ('date',)

class OrderItemsAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'price', 'total', 'user')
    search_fields = ('order__order_no', 'product__product_name', 'user__username')
    list_filter = ('order',)

class PaymentsAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'mobile', 'payments_status', 'mpesa_receipt_number', 'mpesa_transaction_date')
    search_fields = ('user__username', 'mobile', 'mpesa_receipt_number')
    list_filter = ('payments_status', 'mpesa_transaction_date')

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
admin.site.register(Payments, PaymentsAdmin)
admin.site.register(All_Orders, AllOrdersAdmin)
admin.site.register(OrderItems, OrderItemsAdmin)
admin.site.register(RestaurantOrderView, RestaurantOrderViewAdmin)
admin.site.register(Cart, CartAdmin)
