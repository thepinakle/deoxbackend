from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.models import User
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth import login
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.core.mail import send_mail
from django.conf import settings
from .models import Delivery, Hostel, Profile
from restaurant.models import All_Orders, OrderItems, Cart, Products  # Correct import
from .serializers import UserSerializer, ResetPasswordSerializer, DeliverySerializer
from .permissions import IsDeliveryPersonnel
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth.decorators import login_required
import json
from django.views.decorators.csrf import csrf_exempt

class UserCreateView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

class ResetPasswordView(generics.GenericAPIView):
    serializer_class = ResetPasswordSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.get(email=serializer.validated_data['email'])
        self.send_reset_email(user)
        return Response({"detail": "Password reset email has been sent."}, status=status.HTTP_200_OK)

    def send_reset_email(self, user):
        token = RefreshToken.for_user(user).access_token
        reset_url = f"{settings.BACKEND_URL}/reset-password/{token}/"
        send_mail(
            'Password Reset Request',
            f'Click the link to reset your password: {reset_url}',
            settings.EMAIL_HOST_USER,
            [user.email],
            fail_silently=False
        )

def password_reset_confirm(request, uidb64=None, token=None):
    if request.method == 'POST':
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            form = SetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                login(request, user)
                return redirect('password_reset_complete')
        else:
            form = None
    else:
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            form = SetPasswordForm(user)
        else:
            form = None

    return render(request, 'password_reset_confirm.html', {'form': form})

class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]

class DeliveryListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsDeliveryPersonnel]

    def get_queryset(self):
        return All_Orders.objects.filter(payment_verified=True)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        orders_data = [{'order_no': order.order_no, 'total_amount': order.total_amount, 'hostel_name': order.hostel_name, 'block_number': order.block_number, 'room_number': order.room_number, 'status': order.status} for order in queryset]
        return JsonResponse({'orders': orders_data})

class MarkDeliveryCompleteView(generics.UpdateAPIView):
    queryset = Delivery.objects.all()
    serializer_class = DeliverySerializer
    permission_classes = [IsAuthenticated, IsDeliveryPersonnel]

    def update(self, request, *args, **kwargs):
        delivery = self.get_object()
        delivery.status = 'complete'
        delivery.save()
        return Response({"detail": "Delivery marked as complete."}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def assign_hostels_to_delivery_personnel(request):
    delivery_personnel = Profile.objects.filter(role='delivery')
    hostels = Hostel.objects.all()
    for person in delivery_personnel:
        pending_deliveries = Delivery.objects.filter(status='pending', hostel__in=hostels).order_by('hostel')
        if pending_deliveries.exists():
            person.assigned_hostel = pending_deliveries.first().hostel
            person.save()
    return Response({"detail": "Hostels assigned to delivery personnel."}, status=status.HTTP_200_OK)

@login_required
def hostel_orders(request):
    profile = Profile.objects.get(user=request.user)
    if profile.role == 'delivery' and profile.assigned_hostel:
        orders = All_Orders.objects.filter(delivery_address=profile.assigned_hostel)
        return render(request, 'user_management/hostel_orders.html', {'orders': orders})
    else:
        return render(request, 'user_management/hostel_orders.html', {'orders': []})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_order(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        total_amount = data['total_amount']
        items = data['items']
        delivery_address_id = data['delivery_address']
        hostel_name = data['hostel_name']
        block_number = data['block_number']
        room_number = data['room_number']

        delivery_address = Hostel.objects.get(id=delivery_address_id)

        order = All_Orders.objects.create(
            user=request.user,
            total=total_amount,
            delivery_address=delivery_address,
            hostel_name=hostel_name,
            block_number=block_number,
            room_number=room_number
        )
        for item in items:
            OrderItems.objects.create(order=order, product=Products.objects.get(id=item['product_id']), quantity=item['quantity'], price=item['price'], total=item['price'] * item['quantity'], user=request.user)

        return JsonResponse({'order_id': order.id, 'order_no': str(order.order_no), 'total_amount': total_amount})