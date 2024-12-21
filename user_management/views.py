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
from .models import Delivery, Hostel, Profile
from .serializers import UserSerializer, ResetPasswordSerializer, DeliverySerializer
from .permissions import IsDeliveryPersonnel

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
            fail_silently=False,
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
    queryset = Delivery.objects.filter(status='pending')
    serializer_class = DeliverySerializer
    permission_classes = [IsAuthenticated, IsDeliveryPersonnel]

class MarkDeliveryCompleteView(generics.UpdateAPIView):
    queryset = Delivery.objects.all()
    serializer_class = DeliverySerializer
    permission_classes = [IsAuthenticated, IsDeliveryPersonnel]

    def update(self, request, *args, **kwargs):
        delivery = self.get_object()
        delivery.status = 'complete'
        delivery.save()
        return Response({"detail": "Delivery marked as complete."}, status=status.HTTP_200_OK)

class AssignHostelsToDeliveryPersonnelView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        delivery_personnel = Profile.objects.filter(role='delivery')
        hostels = Hostel.objects.all()
        for person in delivery_personnel:
            pending_deliveries = Delivery.objects.filter(status='pending', hostel__in=hostels).order_by('hostel')
            if pending_deliveries.exists():
                person.assigned_hostel = pending_deliveries.first().hostel
                person.save()
        return Response({"detail": "Hostels assigned to delivery personnel."}, status=status.HTTP_200_OK)