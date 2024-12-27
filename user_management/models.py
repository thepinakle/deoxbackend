from django.db import models
from django.contrib.auth.models import User

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
    assigned_hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name='user_management_team_set')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_management_team_set')
    status = models.CharField(max_length=10, choices=[('pending', 'Pending'), ('complete', 'Complete')], default='pending')
    order = models.ForeignKey('restaurant.All_Orders', on_delete=models.CASCADE, related_name='user_management_team_set', default=1)  # Provide a suitable default value

    def __str__(self):
        return f"{self.name} ({self.occupation}) - Assigned to {self.assigned_hostel.name}"

class Profile(models.Model):
    ROLE_CHOICES = (
        ('regular', 'Regular User'),
        ('delivery', 'Delivery Personnel'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='regular')
    assigned_hostel = models.ForeignKey(Hostel, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username}'s profile"

class Delivery(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order = models.ForeignKey('restaurant.All_Orders', on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=[('pending', 'Pending'), ('complete', 'Complete')], default='pending')

    def __str__(self):
        return f"Delivery for {self.user.username} - Order #{self.order.id}"
