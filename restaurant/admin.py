from django.contrib import admin
from .models import  *
admin.site.register(Restaurant)
admin.site.register(Products)
admin.site.register(Payments)
admin.site.register(All_Orders)
admin.site.register(OrderItems)
admin.site.register(RestaurantOrderView)
admin.site.register(Cart)
