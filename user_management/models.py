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
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE)
    order = models.ForeignKey('restaurant.All_Orders', on_delete=models.CASCADE)  # Reference All_Orders from restaurant app
    delivery_person = models.ForeignKey(Team, on_delete=models.CASCADE)

    def __str__(self):
        return f"Delivery for {self.user.username} (Order: {self.order.order_no})"

