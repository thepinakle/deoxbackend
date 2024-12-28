from django.contrib import admin
from .models import Hostel, Team, Profile  # Removed Delivery

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'phone_number', 'address', 'assigned_hostel')
    search_fields = ('user__username', 'role')
    list_filter = ('role',)
    fieldsets = (
        (None, {
            'fields': ('user', 'role', 'phone_number', 'address', 'assigned_hostel')
        }),
    )

@admin.register(Hostel)
class HostelAdmin(admin.ModelAdmin):
    list_display = ('name', 'block', 'room_number')
    search_fields = ('name', 'block', 'room_number')
    list_filter = ('block',)

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'occupation', 'assigned_hostel')
    search_fields = ('name', 'occupation')
    list_filter = ('name',)
