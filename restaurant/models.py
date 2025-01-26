from django.db import models
from django.contrib.auth.models import User
import uuid
from phonenumber_field.modelfields import PhoneNumberField
from user_management.models import Hostel  # Import the Hostel model

class Restaurant(models.Model):
    name = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.TextField(default='Default description')  # Add default value
    picture = models.ImageField(upload_to='restaurant_pictures/', null=True, blank=True)  # Add picture field
    location = models.CharField(max_length=255, default='Default location')  # Add default value

    def __str__(self):
        return self.name

class Products(models.Model):
    product_image = models.ImageField(upload_to="images/")
    product_name = models.CharField(max_length=30)
    product_price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=30)
    description = models.TextField(max_length=200)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)

    def __str__(self):
        return self.product_name

class Cart(models.Model):
    product = models.ForeignKey(Products, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2, editable=False)  # Make price non-editable
    total = models.DecimalField(max_digits=10, decimal_places=2, editable=False)  # Make total non-editable
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    session_key = models.CharField(max_length=40, null=True, blank=True)
    date_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Cart'
        verbose_name_plural = 'Carts'

    def save(self, *args, **kwargs):
        self.price = self.product.product_price  # Fetch price from Products model
        self.total = self.price * self.quantity  # Calculate total
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity} x {self.product.product_name} in cart of {self.user.username}"

class All_Orders(models.Model):
    STATUS_CHOICES = [
        ('picked', 'Picked'),
        ('packed', 'Packed'),
        ('on_transit', 'On Transit'),
        ('complete', 'Complete'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    mobile = PhoneNumberField(null=False, blank=False)
    hostel_name = models.CharField(max_length=100)
    block_number = models.CharField(max_length=100, default='N/A')  # Provide a default value
    room_number = models.CharField(max_length=100)
    date = models.DateTimeField(auto_now_add=True)
    order_no = models.CharField(max_length=100, unique=True, editable=False)  # Make order_no unique and non-editable
    total = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='picked')  # Add delivery status field
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='orders', default=1)  # Provide a suitable default value

    def __str__(self):
        return f"Order #{self.order_no} for {self.user.username}"

class OrderItems(models.Model):
    order = models.ForeignKey(All_Orders, on_delete=models.CASCADE)
    product = models.ForeignKey(Products, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def total(self):
        return self.quantity * self.price

    def __str__(self):
        return f"{self.quantity} x {self.product.product_name}"

class Payments(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    mobile = PhoneNumberField(null=False, blank=False)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payments_status = models.BooleanField(default=False)
    mpesa_receipt_number = models.CharField(max_length=100, blank=True, null=True)
    mpesa_transaction_date = models.DateTimeField(blank=True, null=True)

    def mark_as_paid(self):
        self.payments_status = True
        self.save()

    def __str__(self):
        return f"Payment for {self.user.username} - {self.amount}"

class RestaurantOrderView(models.Model):
    order = models.ForeignKey('All_Orders', on_delete=models.CASCADE)
    restaurant = models.ForeignKey('Restaurant', on_delete=models.CASCADE)
    status = models.CharField(max_length=20, default='pending')  # Provide a default value

    def __str__(self):
        return f"Order {self.order.id} for {self.restaurant.name}"

class Team(models.Model):
    profile_image = models.ImageField(upload_to='images/')
    occupation = models.CharField(max_length=100)
    name = models.CharField(max_length=200)
    assigned_hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name='restaurant_team_set')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='restaurant_team_set', default=1)  # Provide a suitable default value
    status = models.CharField(max_length=10, choices=[('pending', 'Pending'), ('complete', 'Complete')], default='pending')
    order = models.ForeignKey('restaurant.All_Orders', on_delete=models.CASCADE, related_name='restaurant_team_set', default=1)  # Provide a suitable default value

    def __str__(self):
        return f"{self.name} ({self.occupation}) - Assigned to {self.assigned_hostel.name}"
