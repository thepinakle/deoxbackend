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

logger = logging.getLogger(__name__)

def format_phone_number(phone_number):
    # Remove any leading '+' sign and ensure the number is in international format
    if phone_number.startswith('+'):
        phone_number = phone_number[1:]
    return phone_number

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

            # Initiate M-Pesa payment request
            transaction_desc = f"Payment for Order"
            account_reference = f"OrderPayment"
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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def view_cart(request):
    cart_items = Cart.objects.filter(user=request.user)
    cart_data = [{'product_name': item.product.product_name, 'quantity': item.quantity, 'price': item.price, 'total': item.total} for item in cart_items]
    return JsonResponse({'cart': cart_data})

@csrf_exempt
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
def mpesa_callback(request):
    data = json.loads(request.body)
    result_code = data['Body']['stkCallback']['ResultCode']
    if result_code == 0:
        mpesa_receipt_number = data['Body']['stkCallback']['CallbackMetadata']['Item'][1]['Value']
        transaction_date = data['Body']['stkCallback']['CallbackMetadata']['Item'][3]['Value']
        phone_number = data['Body']['stkCallback']['CallbackMetadata']['Item'][4]['Value']
        payment = Payments.objects.get(mobile=phone_number, payments_status=False)
        payment.mpesa_receipt_number = mpesa_receipt_number
        payment.mpesa_transaction_date = datetime.strptime(str(transaction_date), '%Y%m%d%H%M%S')
        payment.mark_as_paid()

        # Create the order after successful payment
        order = All_Orders.objects.create(
            user=payment.user,
            mobile=payment.mobile,
            total=payment.amount,
            hostel_name=payment.hostel_name,
            block_number=payment.block_number,
            room_number=payment.room_number
        )
        for item in payment.items:
            product = Products.objects.get(product_name=item['product_name'], product_price=item['product_price'])
            OrderItems.objects.create(
                order=order,
                product=product,
                quantity=item['quantity'],
                price=product.product_price,  # Set the price from the product
                total=product.product_price * item['quantity'],  # Calculate and set the total
                user=payment.user,  # Set the user
                delivery_status='pending'  # Set the default delivery status
            )

    return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})