from django.db import models
from django.contrib.auth.models import User
from phonenumber_field.modelfields import PhoneNumberField

class Hostel(models.Model):
    name = models.CharField(max_length=100, unique=True)
    block = models.CharField(max_length=100, blank=True, null=True)
    room_number = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name}, Block: {self.block if self.block else 'No Block'}, Room: {self.room_number}"

class Team(models.Model):
    profile_image = models.ImageField(upload_to='images/')
    occupation = models.CharField(max_length=100)
    name = models.CharField(max_length=200)
    assigned_hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name} ({self.occupation}) - Assigned to {self.assigned_hostel.name}"

class Delivery(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('complete', 'Complete'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE)
    order = models.ForeignKey('restaurant.All_Orders', on_delete=models.CASCADE)  # Reference All_Orders from restaurant app
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"Delivery for {self.user.username} to {self.hostel.name}, Order ID: {self.order.id}"

class Profile(models.Model):
    ROLE_CHOICES = (
        ('regular', 'Regular User'),
        ('delivery', 'Delivery Personnel'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = PhoneNumberField(null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='regular')
    assigned_hostel = models.ForeignKey(Hostel, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username}'s profile"
