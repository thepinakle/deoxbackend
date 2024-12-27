from django.db import models
from django.contrib.auth.models import User
import uuid
from phonenumber_field.modelfields import PhoneNumberField
from user_management.models import Hostel  # Import the Hostel model

class Restaurant(models.Model):
    name = models.CharField(max_length=255)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

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
        verbose_name = 'cart'
        verbose_name_plural = 'carts'

    def save(self, *args, **kwargs):
        self.price = self.product.product_price  # Fetch price from Products model
        self.total = self.price * self.quantity  # Calculate total
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Cart for {self.user.username}"

class All_Orders(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    mobile = PhoneNumberField(null=False, blank=False)
    hostel_name = models.CharField(max_length=100, default="Unknown Hostel")
    block_number = models.CharField(max_length=100, blank=True, null=True, default="Unknown Block")
    room_number = models.CharField(max_length=100, default="Unknown Room")
    date = models.DateTimeField(auto_now_add=True)
    order_no = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Order #{self.order_no} for {self.user.username}"

class OrderItems(models.Model):
    order = models.ForeignKey(All_Orders, on_delete=models.CASCADE)
    product = models.ForeignKey(Products, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Ensure this field is included
    total = models.DecimalField(max_digits=10, decimal_places=2)
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # Add the user field
    delivery_status = models.CharField(max_length=20, default='pending')  # Add delivery_status with default value

    def save(self, *args, **kwargs):
        self.price = self.product.product_price  # Fetch price from Products model
        self.total = self.price * self.quantity  # Calculate total
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order Item: {self.product.product_name} (x{self.quantity})"

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
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    order = models.ForeignKey(All_Orders, on_delete=models.CASCADE)
    ordered_products = models.ManyToManyField(OrderItems)

    def __str__(self):
        return f"Order #{self.order.order_no} for {self.restaurant.name}"

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
