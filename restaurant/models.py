from django.db import models
from django.contrib.auth.models import User
import uuid
from phonenumber_field.modelfields import PhoneNumberField
import random
import string


class Restaurant(models.Model):
    name = models.CharField(max_length=255)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Products(models.Model):
    product_image = models.ImageField(upload_to="images/")
    product_name = models.CharField(max_length=30)
    product_price = models.CharField(max_length=20)
    category = models.CharField(max_length=30)
    description = models.TextField(max_length=200)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)

    def __str__(self):
        return self.product_name


class Cart(models.Model):
    product = models.ForeignKey(Products, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    session_key = models.CharField(max_length=40, null=True, blank=True)
    date_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'cart'
        verbose_name_plural = 'carts'

    def __str__(self):
        return f"Cart for {self.user.username}"


class All_Orders(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    mobile = PhoneNumberField(null=False, blank=False)
    delivery_address = models.ForeignKey('user_management.Hostel', on_delete=models.CASCADE)  # Reference Hostel from user_management
    date = models.DateTimeField(auto_now_add=True)
    order_no = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Order #{self.order_no} by {self.user.username}"


class OrderItems(models.Model):
    order = models.ForeignKey(All_Orders, on_delete=models.CASCADE)
    product = models.ForeignKey(Products, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1, editable=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    delivery_status = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=[
            ('packed', 'Packed'),
            ('picked', 'Picked'),
            ('delivered', 'Delivered'),
        ],
        default='packed'
    )
    delivery_code = models.CharField(max_length=6, null=True, blank=True, unique=True)

    def __str__(self):
        return f"Item: {self.product.product_name} (Status: {self.status})"

    def generate_delivery_code(self):
        """Generate a random delivery code."""
        if not self.delivery_code:
            self.delivery_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            self.save()
        return self.delivery_code

    def mark_as_packed(self):
        self.status = 'packed'
        self.save()

    def mark_as_picked(self):
        self.status = 'picked'
        self.save()

    def mark_as_delivered(self, user_code):
        if user_code == self.delivery_code:
            self.status = 'delivered'
            self.save()
        else:
            raise ValueError("Invalid delivery code.")


class Payments(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order_no = models.ForeignKey(All_Orders, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    mobile = PhoneNumberField(blank=False, null=False)
    date = models.DateTimeField(auto_now_add=True)
    transaction_id = models.CharField(max_length=100)
    payments_status = models.BooleanField(default=False)

    def __str__(self):
        return f"Payment for Order #{self.order_no.order_no} by {self.user.username}"

    def mark_as_paid(self):
        """Mark the payment as completed."""
        self.payments_status = True
        self.save()


class RestaurantOrderView(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    order = models.ForeignKey(All_Orders, on_delete=models.CASCADE)
    ordered_products = models.ManyToManyField(OrderItems)

    def __str__(self):
        return f"Order #{self.order.order_no} for {self.restaurant.name}"
