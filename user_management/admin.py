from django.contrib import admin
from .models import Hostel, Team, Delivery, Profile

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

admin.site.register(Hostel)
admin.site.register(Team)
admin.site.register(Delivery)
