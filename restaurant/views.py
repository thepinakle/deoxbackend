import logging
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from .models import All_Orders, OrderItems, Cart, Products, Payments
from .mpesa import lipa_na_mpesa_online  # Ensure this import is correct
import json
from datetime import datetime
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample

logger = logging.getLogger(__name__)

def format_phone_number(phone_number):
    # Remove any leading '+' sign and ensure the number is in international format
    if phone_number.startswith('+'):
        phone_number = phone_number[1:]
    return phone_number

@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'total_amount': openapi.Schema(type=openapi.TYPE_NUMBER, description='Total amount of the order'),
            'items': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_OBJECT), description='List of items in the order'),
            'hostel_name': openapi.Schema(type=openapi.TYPE_STRING, description='Name of the hostel'),
            'block_number': openapi.Schema(type=openapi.TYPE_STRING, description='Block number'),
            'room_number': openapi.Schema(type=openapi.TYPE_STRING, description='Room number'),
            'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description='Phone number'),
        },
        required=['total_amount', 'items', 'hostel_name', 'block_number', 'room_number', 'phone_number']
    ),
    responses={200: 'Order created successfully', 400: 'Invalid input'}
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_order(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            logger.info(f"Request data: {data}")
            total_amount = data['total_amount']
            items = data['items']
            hostel_name = data['hostel_name']
            block_number = data['block_number']
            room_number = data['room_number']
            phone_number = format_phone_number(data['phone_number'])

            # Generate the transaction description with product names
            product_names = [item['product_name'] for item in items]
            transaction_desc = f"Payment for: {', '.join(product_names)}"
            account_reference = f"OrderPayment"

            # Initiate M-Pesa payment request
            response = lipa_na_mpesa_online(phone_number, total_amount, account_reference, transaction_desc)

            if 'errorCode' in response:
                logger.error(f"M-Pesa error: {response['errorMessage']}")
                return JsonResponse({'error': response['errorMessage'], 'mpesa_response': response}, status=400)

            # Save payment details for callback verification
            Payments.objects.create(
                user=request.user,
                mobile=phone_number,
                amount=total_amount,
                payments_status=False,
                mpesa_receipt_number='',
                mpesa_transaction_date=None
            )

            return JsonResponse({'message': 'Payment initiated successfully. Please complete the payment on your phone.', 'mpesa_response': response})
        except json.JSONDecodeError:
            logger.error("Invalid JSON payload")
            return JsonResponse({'error': 'Invalid JSON payload'}, status=400)
        except KeyError as e:
            logger.error(f"Missing key in request data: {e}")
            return JsonResponse({'error': f"Missing key in request data: {e}"}, status=400)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return JsonResponse({'error': 'An unexpected error occurred'}, status=500)

@swagger_auto_schema(
    method='post',
    responses={200: 'Delivery marked as complete', 400: 'Invalid request'}
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_delivery_complete(request, pk):
    try:
        order = All_Orders.objects.get(pk=pk)
        order.status = 'complete'
        order.save()
        return JsonResponse({"detail": "Delivery marked as complete."}, status=200)
    except All_Orders.DoesNotExist:
        return JsonResponse({"detail": "Order not found."}, status=404)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_orders(request):
    orders = All_Orders.objects.filter(user=request.user)
    orders_data = [{'order_no': str(order.order_no), 'total_amount': order.total, 'status': order.status} for order in orders]
    return JsonResponse({'orders': orders_data})

@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'item_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Item ID'),
            'quantity': openapi.Schema(type=openapi.TYPE_INTEGER, description='Quantity'),
        },
        required=['item_id', 'quantity']
    ),
    responses={200: 'Item added to cart', 400: 'Invalid input'}
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_to_cart(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        product_id = data['product_id']
        quantity = data['quantity']

        product = Products.objects.get(id=product_id)
        cart_item, created = Cart.objects.get_or_create(user=request.user, product=product)
        if not created:
            cart_item.quantity += quantity
        else:
            cart_item.quantity = quantity
        cart_item.save()

        return JsonResponse({'message': 'Item added to cart', 'cart_item_id': cart_item.id})

@swagger_auto_schema(
    method='get',
    responses={200: 'Cart retrieved successfully'}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def view_cart(request):
    cart_items = Cart.objects.filter(user=request.user)
    cart_data = [{'product_name': item.product.product_name, 'quantity': item.quantity, 'price': item.price, 'total': item.total} for item in cart_items]
    return JsonResponse({'cart': cart_data})

@csrf_exempt
@extend_schema(
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'phone_number': {'type': 'string', 'description': 'Phone number'},
                'amount': {'type': 'number', 'description': 'Amount'},
                'order_no': {'type': 'string', 'description': 'Order number'},
                'transaction_desc': {'type': 'string', 'description': 'Transaction description'},
                'account_reference': {'type': 'string', 'description': 'Account reference'},
            },
            'required': ['phone_number', 'amount', 'order_no', 'transaction_desc', 'account_reference']
        }
    },
    responses={
        200: OpenApiExample(
            'Success',
            value={'status': 'success', 'message': 'Payment request sent successfully'}
        ),
        400: OpenApiExample(
            'Invalid input',
            value={'status': 'error', 'message': 'Invalid input'}
        )
    }
)
def mpesa_payment_request(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        phone_number = data['phone_number']
        amount = data['amount']
        order_no = data['order_no']
        transaction_desc = data['transaction_desc']
        account_reference = data['account_reference']
        response = lipa_na_mpesa_online(phone_number, amount, account_reference, transaction_desc)
        return JsonResponse(response)

@csrf_exempt
@extend_schema(
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'TransactionType': {'type': 'string', 'description': 'Transaction type'},
                'TransID': {'type': 'string', 'description': 'Transaction ID'},
                'TransTime': {'type': 'string', 'description': 'Transaction time'},
                'TransAmount': {'type': 'number', 'description': 'Transaction amount'},
                'BusinessShortCode': {'type': 'string', 'description': 'Business short code'},
                'BillRefNumber': {'type': 'string', 'description': 'Bill reference number'},
                'InvoiceNumber': {'type': 'string', 'description': 'Invoice number'},
                'OrgAccountBalance': {'type': 'number', 'description': 'Organization account balance'},
                'ThirdPartyTransID': {'type': 'string', 'description': 'Third party transaction ID'},
                'MSISDN': {'type': 'string', 'description': 'MSISDN'},
                'FirstName': {'type': 'string', 'description': 'First name'},
                'MiddleName': {'type': 'string', 'description': 'Middle name'},
                'LastName': {'type': 'string', 'description': 'Last name'},
            },
            'required': [
                'TransactionType', 'TransID', 'TransTime', 'TransAmount', 'BusinessShortCode',
                'BillRefNumber', 'InvoiceNumber', 'OrgAccountBalance', 'ThirdPartyTransID',
                'MSISDN', 'FirstName', 'MiddleName', 'LastName'
            ]
        }
    },
    responses={
        200: OpenApiExample(
            'Success',
            value={'status': 'success', 'message': 'Callback received successfully'}
        ),
        400: OpenApiExample(
            'Invalid input',
            value={'status': 'error', 'message': 'Invalid input'}
        )
    }
)
def mpesa_callback(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        # Your existing code here
        pass