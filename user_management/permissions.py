from rest_framework.permissions import BasePermission

class IsDeliveryPersonnel(BasePermission):
    """
    Custom permission to only allow delivery personnel to access certain views.
    """
    def has_permission(self, request, view):
        return request.user.profile.role == 'delivery'