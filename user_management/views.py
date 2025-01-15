from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_str, force_bytes
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
from .models import Delivery, Hostel, Profile, Team
from restaurant.models import All_Orders, OrderItems, Cart, Products  # Correct import
from .serializers import UserSerializer, ResetPasswordSerializer, DeliverySerializer, OrderSerializer, PasswordResetSerializer, SetNewPasswordSerializer
from .permissions import IsDeliveryPersonnel
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth.decorators import login_required
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string

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

@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'username': openapi.Schema(type=openapi.TYPE_STRING, description='Username'),
            'password': openapi.Schema(type=openapi.TYPE_STRING, description='Password'),
        },
        required=['username', 'password']
    ),
    responses={200: 'Token obtained successfully', 400: 'Invalid credentials'}
)
@api_view(['POST'])
@permission_classes([AllowAny])
def token_obtain_pair(request):

    pass

@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'refresh': openapi.Schema(type=openapi.TYPE_STRING, description='Refresh token'),
        },
        required=['refresh']
    ),
    responses={200: 'Token refreshed successfully', 400: 'Invalid token'}
)
@api_view(['POST'])
@permission_classes([AllowAny])
def token_refresh(request):
    pass

@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'username': openapi.Schema(type=openapi.TYPE_STRING, description='Username'),
            'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email'),
            'password': openapi.Schema(type=openapi.TYPE_STRING, description='Password'),
        },
        required=['username', 'email', 'password']
    ),
    responses={201: 'User created successfully', 400: 'Invalid input'}
)
@api_view(['POST'])
@permission_classes([AllowAny])
def user_create(request):
    
    pass

@extend_schema(
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'username': {'type': 'string', 'description': 'Username'},
                'password': {'type': 'string', 'description': 'Password'},
            },
            'required': ['username', 'password']
        }
    },
    responses={
        200: OpenApiExample(
            'Success',
            value={'status': 'success', 'message': 'Login successful'}
        ),
        400: OpenApiExample(
            'Invalid credentials',
            value={'status': 'error', 'message': 'Invalid credentials'}
        )
    }
)
@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):

    pass

@extend_schema(
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'email': {'type': 'string', 'description': 'Email'},
            },
            'required': ['email']
        }
    },
    responses={
        200: OpenApiExample(
            'Success',
            value={'status': 'success', 'message': 'Password reset email sent'}
        ),
        400: OpenApiExample(
            'Invalid email',
            value={'status': 'error', 'message': 'Invalid email'}
        )
    }
)
@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    
    pass

@extend_schema(
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'new_password': {'type': 'string', 'description': 'New password'},
            },
            'required': ['new_password']
        }
    },
    responses={
        200: OpenApiExample(
            'Success',
            value={'status': 'success', 'message': 'Password reset successful'}
        ),
        400: OpenApiExample(
            'Invalid token',
            value={'status': 'error', 'message': 'Invalid token'}
        )
    }
)
@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password_confirm(request, uidb64, token):

    pass

@swagger_auto_schema(
    method='get',
    responses={200: 'Delivery list retrieved successfully'}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def delivery_list(request):
    
    pass

@swagger_auto_schema(
    method='post',
    responses={200: 'Delivery marked as complete', 400: 'Invalid request'}
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_delivery_complete(request, pk):
    
    pass

@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'delivery_person_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Delivery person ID'),
            'hostel_ids': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_INTEGER), description='List of hostel IDs'),
        },
        required=['delivery_person_id', 'hostel_ids']
    ),
    responses={200: 'Hostels assigned successfully', 400: 'Invalid input'}
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def assign_hostels(request):
    # Your existing code here
    pass

@swagger_auto_schema(
    method='get',
    responses={200: 'Hostel orders retrieved successfully'}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hostel_orders(request):
    pass

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_orders_by_hostel_block(request):
    user = request.user
    team_member = Team.objects.get(user=user)
    hostel_block_number = team_member.assigned_hostel.block
    orders = All_Orders.objects.filter(block_number=hostel_block_number)
    return render(request, 'orders_by_hostel_block.html', {'orders': orders, 'team_member': team_member})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_orders_by_team_member(request):
    user = request.user
    team_member = get_object_or_404(Team, user=user)
    hostel_block_number = team_member.assigned_hostel.block
    orders = All_Orders.objects.filter(block_number=hostel_block_number)
    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_request(request):
    serializer = PasswordResetSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data['email']
        users = User.objects.filter(email=email)
        if users.exists():
            for user in users:
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                reset_link = f"{settings.FRONTEND_URL}/reset-password-confirm/{uid}/{token}/"
                mail_subject = 'Password Reset Request'
                message = f"Hi {user.username},\n\nYou requested a password reset. Click the link below to reset your password:\n{reset_link}\n\nIf you did not request this, please ignore this email."
                send_mail(mail_subject, message, settings.EMAIL_HOST_USER, [user.email])
            return Response({'message': 'Password reset link has been sent to your email.'}, status=status.HTTP_200_OK)
        return Response({'message': 'No user found with this email address.'}, status=status.HTTP_404_NOT_FOUND)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_confirm(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        serializer = SetNewPasswordSerializer(data=request.data)
        if serializer.is_valid():
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({'message': 'Password has been reset successfully.'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    return Response({'message': 'Invalid token or user ID.'}, status=status.HTTP_400_BAD_REQUEST)

# View to retrieve the authenticated user's profile (username and email)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])  # Ensure the user is authenticated
@extend_schema(
    responses={
        200: UserProfileSerializer,
        401: OpenApiExample(
            'Unauthorized',
            value={'status': 'error', 'message': 'Authentication required'}
        )
    }
)
def user_profile(request):
    try:
        # Get the current authenticated user
        user = request.user

        # Serialize the user data (username and email)
        serializer = UserProfileSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    except User.DoesNotExist:
        return Response(
            {'status': 'error', 'message': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )