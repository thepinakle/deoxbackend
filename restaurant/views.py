import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from .models import All_Orders, OrderItems, Cart, Products, Payments, Restaurant
from .mpesa import lipa_na_mpesa_online  # Ensure this import is correct
import json
from datetime import datetime
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import uuid
from .serializers import AllOrdersSerializer
from .serializers import UpdateDeliveryStatusSerializer
from rest_framework import serializers
from .serializers import RestaurantSerializer, ProductSerializer
from rest_framework.permissions import IsAdminUser
from decimal import Decimal
from .utils import calculate_delivery_fee
from openai import OpenAI
import os


client = OpenAI(api_key="sk-0858dbbbdf494ff08e518e49be95e1a9", base_url="https://api.deepseek.com")

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.http import JsonResponse
import logging
from openai import OpenAI


logger = logging.getLogger(__name__)

client = OpenAI(api_key="sk-0858dbbbdf494ff08e518e49be95e1a9", base_url="https://api.deepseek.com")

# Define the request body schema
chat_request_body = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'message': openapi.Schema(type=openapi.TYPE_STRING, description='User message')
    },
    required=['message']
)

# Define the response body schema
chat_response_body = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'message': openapi.Schema(type=openapi.TYPE_STRING, description='Bot response')
    }
)

@swagger_auto_schema(
    method='post',
    operation_description="Chat with the bot to get food recommendations and advice",
    request_body=chat_request_body,
    responses={
        200: openapi.Response('Successful operation', chat_response_body),
        400: openapi.Response('No message provided'),
        500: openapi.Response('An unexpected error occurred')
    }
)
@api_view(['POST'])
@permission_classes([AllowAny])
def chat_with_bot(request):
    user_input = request.data.get('message')
    if not user_input:
        return JsonResponse({'error': 'No message provided'}, status=400)

    messages = [
        {"role": "system", "content": """You are a fun assistant for a food order platform named deox located at egerton university founded by Deon.
         Your goal is to help users find the perfect food order. offer advice on healthy food options, and provide recommendations based on user preferences.
         You should be able to answer questions about the food menu, suggest dishes, and offer suggestions for dietary restrictions here being creative if user has not provided much info
         students are more familiar with njokerio, gate or palatte this are places the take their food from.
         
         Show your reasoning process in this format:

1. THOUGHT PROCESS: Break down how you're approaching the question
2. ANALYSIS: Explain key considerations and factors
3. CONCLUSION: Provide your final response

Keep the tone light and entertaining while showing your work."""},
        {"role": "user", "content": user_input}
    ]

    try:
        response = client.chat.completions.create(
            model="deepseek-reasoner",
            messages=messages,
            temperature=1.0,
            stream=True
        )

        bot_response = ""
        for chunk in response:
            if chunk.choices[0].delta.content:
                bot_response += chunk.choices[0].delta.content

        return JsonResponse({'message': bot_response}, status=200)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return JsonResponse({'error': 'An unexpected error occurred'}, status=500)



@swagger_auto_schema(
    method='get',
    operation_description="Retrieve the delivery fee for the items in the user's cart",
    responses={
        200: openapi.Response('Delivery fee calculated successfully', openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'message': openapi.Schema(type=openapi.TYPE_STRING),
                'total_price': openapi.Schema(type=openapi.TYPE_NUMBER, format='decimal'),
                'delivery_fee': openapi.Schema(type=openapi.TYPE_NUMBER, format='decimal')
            }
        )),
        400: openapi.Response('Cart is empty'),
        500: openapi.Response('An unexpected error occurred')
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_delivery_fee(request):
    try:
        # Retrieve the items in the user's cart
        cart_items = Cart.objects.filter(user=request.user)
        if not cart_items.exists():
            return JsonResponse({'error': 'Cart is empty'}, status=400)

        # Calculate the total price of the items in the cart
        total_price = sum(item.quantity * item.product.product_price for item in cart_items)

        # Calculate the delivery fee based on the total price
        delivery_fee = calculate_delivery_fee(total_price)

        return JsonResponse({
            'message': 'Delivery fee calculated successfully',
            'total_price': total_price,
            'delivery_fee': delivery_fee
        })
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return JsonResponse({'error': 'An unexpected error occurred'}, status=500)

# Add the new view to your urls.py

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from .models import All_Orders
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.http import JsonResponse
from django.utils import timezone
import json
from datetime import datetime
from rest_framework import permissions

 # Import the delivery fee function



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
            'product_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Product ID'),
            'quantity': openapi.Schema(type=openapi.TYPE_INTEGER, description='Quantity'),
        },
        required=['product_id', 'quantity']
    ),
    responses={200: 'Item added to cart', 400: 'Invalid input'}
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_to_cart(request):
    try:
        product_id = request.data.get('product_id')
        product = Products.objects.get(id=product_id)
        cart_item, created = Cart.objects.get_or_create(user=request.user, product=product)
        if not created:
            cart_item.quantity += 1
            cart_item.save()
        return JsonResponse({'message': 'Item added to cart', 'quantity': cart_item.quantity}, status=200)
    except Products.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return JsonResponse({'error': 'An unexpected error occurred'}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def remove_to_cart(request):
    try:
        product_id = request.data.get('product_id')
        product = Products.objects.get(id=product_id)
        cart_item, created = Cart.objects.get_or_create(user=request.user, product=product)
        if not created:
            cart_item.quantity -= 1
            cart_item.save()
        return JsonResponse({'message': 'Item removed from cart', 'quantity': cart_item.quantity}, status=200)
    except Products.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return JsonResponse({'error': 'An unexpected error occurred'}, status=500)





@swagger_auto_schema(
    method='post',
    operation_description="Remove an item from the cart",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'product_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of the product to remove')
        }
    ),
    responses={
        200: openapi.Response('Item removed from cart', openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'message': openapi.Schema(type=openapi.TYPE_STRING),
                'quantity': openapi.Schema(type=openapi.TYPE_INTEGER)
            }
        )),
        404: openapi.Response('Product not found'),
        404: openapi.Response('Item not in cart'),
        500: openapi.Response('An unexpected error occurred')
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def remove_from_cart(request):
    try:
        product_id = request.data.get('product_id')
        product = Products.objects.get(product_id=product_id)
        cart_item = Cart.objects.get(user=request.user, product=product)
        if (cart_item.quantity > 1):
            cart_item.quantity -= 1
            cart_item.save()
        else:
            cart_item.delete()
        return JsonResponse({'message': 'Item removed from cart', 'quantity': cart_item.quantity if cart_item.quantity > 0 else 0}, status=200)
    except Products.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)
    except Cart.DoesNotExist:
        return JsonResponse({'error': 'Item not in cart'}, status=404)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return JsonResponse({'error': 'An unexpected error occurred'}, status=500)

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

@swagger_auto_schema(
    method='get',
    operation_description="Retrieve the delivery fee for the items in the user's cart",
    responses={
        200: openapi.Response('Delivery fee calculated successfully', openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'message': openapi.Schema(type=openapi.TYPE_STRING),
                'total_price': openapi.Schema(type=openapi.TYPE_NUMBER, format='decimal'),
                'delivery_fee': openapi.Schema(type=openapi.TYPE_NUMBER, format='decimal')
            }
        )),
        400: openapi.Response('Cart is empty'),
        500: openapi.Response('An unexpected error occurred')
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_delivery_fee(request):
    try:
        # Retrieve the items in the user's cart
        cart_items = Cart.objects.filter(user=request.user)
        if not cart_items.exists():
            return JsonResponse({'error': 'Cart is empty'}, status=400)

        # Calculate the total price of the items in the cart
        total_price = sum(item.quantity * item.product.product_price for item in cart_items)

        # Calculate the delivery fee based on the total price
        delivery_fee = calculate_delivery_fee(total_price)

        return JsonResponse({
            'message': 'Delivery fee calculated successfully',
            'total_price': total_price,
            'delivery_fee': delivery_fee
        })
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return JsonResponse({'error': 'An unexpected error occurred'}, status=500)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return JsonResponse({'error': 'An unexpected error occurred'}, status=500)

@csrf_exempt
@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'hostel_name': openapi.Schema(type=openapi.TYPE_STRING, description='Hostel name'),
            'block_number': openapi.Schema(type=openapi.TYPE_STRING, description='Block number'),
            'room_number': openapi.Schema(type=openapi.TYPE_STRING, description='Room number'),
            'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description='Phone number')
        },
        required=['hostel_name', 'block_number', 'room_number', 'phone_number']
    ),
    responses={200: 'Order created and payment initiated', 400: 'Invalid input'}
)

  # Importing the utility function


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_order(request):
    try:
        # Parse incoming request data
        data = json.loads(request.body)
        logger.info(f"Request payload: {data}")
        
        hostel_name = data['hostel_name']
        block_number = data['block_number']
        room_number = data['room_number']
        phone_number = format_phone_number(data['phone_number'])

        # Retrieve cart items for the current user
        cart_items = Cart.objects.filter(user=request.user)
        if not cart_items.exists():
            return JsonResponse({'error': 'Cart is empty'}, status=400)

        # Ensure total_amount is a float (or str if you prefer)
        total_amount = sum(float(item.total) for item in cart_items)  # Convert Decimal to float

        # Calculate delivery fee based on total amount of ordered items
        def calculate_delivery_fee(total_amount):
            if total_amount < 75:
                return 11
            elif 75 <= total_amount <= 150:
                return 21
            elif 151 <= total_amount <= 200:
                return 31
            elif 201 <= total_amount <= 300:
                return 36
            elif 301 <= total_amount <= 400:
                return 51
            elif 401 <= total_amount <= 500:
                return 55
            elif 501 <= total_amount <= 600:
                return 60
            else:  # for amounts above 600
                return 70

        # Calculate the delivery fee and total amount with delivery
        delivery_fee = calculate_delivery_fee(total_amount)
        total_amount_with_delivery = total_amount + delivery_fee

        # Generate a unique order number
        order_no = f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"

        # Initiate M-Pesa payment and get the response
        transaction_desc = f"Payment for order {order_no}"
        account_reference = f"Order {order_no}"
        mpesa_response = lipa_na_mpesa_online(phone_number, total_amount_with_delivery, account_reference, transaction_desc)

        # Check if the M-Pesa response contains an error code or lacks a transaction code
        if 'errorCode' in mpesa_response:
            return JsonResponse({'error': mpesa_response['errorMessage'], 'mpesa_response': mpesa_response}, status=400)

        # Extract M-Pesa transaction code from the response (assuming it's present)
        mpesa_transaction_code = mpesa_response.get('transactionCode', None)

        # If no transaction code, wait for 30 seconds before retrying
        if not mpesa_transaction_code:
            # Wait for 30 seconds
            time.sleep(30)

            # Retry the transaction to fetch the transaction code (you may want to implement this as a loop)
            mpesa_response = lipa_na_mpesa_online(phone_number, total_amount_with_delivery, account_reference, transaction_desc)
            mpesa_transaction_code = mpesa_response.get('transactionCode', None)

            # If the transaction code is still not found after 30 seconds, return an error
            if not mpesa_transaction_code:
                return JsonResponse({'error': 'Payment failed, no transaction code received after waiting 30 seconds'}, status=400)

        # Proceed to create the order since the transaction code is received
        order = All_Orders.objects.create(
            user=request.user,
            total=total_amount_with_delivery,  # Store total amount with delivery fee
            hostel_name=hostel_name,
            block_number=block_number,
            room_number=room_number,
            mobile=phone_number,
            order_no=order_no,
            mpesa_transaction_code=mpesa_transaction_code  # Store the M-Pesa transaction code
        )

        # Create order items
        for item in cart_items:
            OrderItems.objects.create(order=order, product=item.product, quantity=item.quantity, price=float(item.price))  # Convert Decimal to float
            item.delete()  # Remove item from cart after adding to order

        # Create a payment record (assuming payment status is initially 'False' until confirmed)
        Payments.objects.create(
            user=request.user,
            mobile=phone_number,
            amount=total_amount_with_delivery,  # Include the delivery fee in the payment
            payments_status=False,
            mpesa_receipt_number='',
            mpesa_transaction_date=None
        )

        # Return response with the created order details
        return JsonResponse({
            'message': 'Order created and payment initiated successfully',
            'order_id': order.id,
            'order_no': order.order_no,
            'mpesa_transaction_code': mpesa_transaction_code,
            'total_amount_with_delivery': total_amount_with_delivery
        })

    except json.JSONDecodeError:
        logger.error("Invalid JSON payload")
        return JsonResponse({'error': 'Invalid JSON payload'}, status=400)
    except KeyError as e:
        logger.error(f"Missing key in request payload: {e}")
        return JsonResponse({'error': f"Missing key: {e}"}, status=400)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return JsonResponse({'error': 'An unexpected error occurred'}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_orders(request):
    orders = All_Orders.objects.filter(user=request.user)
    orders_data = [{'order_no': str(order.order_no), 'total_amount': order.total, 'status': order.status} for order in orders]
    return JsonResponse({'orders': orders_data})

@swagger_auto_schema(
    method='get',
    responses={200: 'Cart retrieved successfully'}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def view_cart(request):
    cart_items = Cart.objects.filter(user=request.user)
    cart_data = [{
        'id': item.id,
        'product_name': item.product.product_name,
        'quantity': item.quantity,
        'price': item.price,
        'total': item.total,
        'image': item.product.product_image.url  # Include the image URL if applicable
    } for item in cart_items]
    return JsonResponse({'cart': cart_data})

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(Cart, id=item_id, user=request.user)
    cart_item.delete()
    return JsonResponse({'status': 'success', 'message': 'Item removed fromt cart'})

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
        pass

def restaurant_list(request):
    restaurants = Restaurant.objects.all()
    return render(request, 'restaurant_list.html', {'restaurants': restaurants})

def restaurant_detail(request, restaurant_id):
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    products = Products.objects.filter(restaurant=restaurant)
    return render(request, 'restaurant_detail.html', {'restaurant': restaurant, 'products': products})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_orders_by_restaurant(request, restaurant_name):
    if not request.user.is_staff:
        return Response({'detail': 'You do not have permission to perform this action.'}, status=status.HTTP_403_FORBIDDEN)

    restaurant = get_object_or_404(Restaurant, name=restaurant_name)
    orders = All_Orders.objects.filter(restaurant=restaurant)
    serializer = AllOrdersSerializer(orders, many=True)
    return Response(serializer.data)


@swagger_auto_schema(
    method='get',
    operation_description="Retrieve a list of all restaurants along with their associated products.",
    responses={
        200: openapi.Response(
            description="A list of restaurants with details and products.",
            examples={
                "application/json": [
                    {
                        "id": 1,
                        "name": "Restaurant A",
                        "description": "Best restaurant in town",
                        "location": "123 Main Street",
                        "picture": "http://example.com/media/restaurant_pictures/restaurant_a.jpg",
                        "products": [
                            {
                                "id": 1,
                                "product_name": "Pizza",
                                "product_price": "10.99",
                                "category": "Food",
                                "description": "Delicious cheese pizza",
                                "product_image": "http://example.com/media/images/pizza.jpg"
                            },
                            {
                                "id": 2,
                                "product_name": "Burger",
                                "product_price": "8.99",
                                "category": "Food",
                                "description": "Juicy beef burger",
                                "product_image": "http://example.com/media/images/burger.jpg"
                            }
                        ]
                    },
                    {
                        "id": 2,
                        "name": "Restaurant B",
                        "description": "Fine dining experience",
                        "location": "456 Elm Street",
                        "picture": None,
                        "products": []
                    }
                ]
            }
        ),
    },
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])  # Public access
def api_restaurant_list(request):
    restaurants = Restaurant.objects.all()
    data = []

    for restaurant in restaurants:
        products = Products.objects.filter(restaurant=restaurant)
        serialized_products = ProductSerializer(products, many=True).data
        data.append({
            'id': restaurant.id,
            'name': restaurant.name,
            'description': restaurant.description,
            'location': restaurant.location,
            'picture': restaurant.picture.url if restaurant.picture else None,
            'products': serialized_products,
        })

    return Response(data)



@swagger_auto_schema(
    method='get',
    operation_description="Retrieve products filtered by category.",
    responses={
        200: openapi.Response(
            description="List of products in the given category.",
            schema=ProductSerializer(many=True)
        ),
        404: openapi.Response(
            description="No products found in the specified category."
        ),
    },
    manual_parameters=[
        openapi.Parameter(
            'category',
            openapi.IN_PATH,
            description="The category to filter products by.",
            type=openapi.TYPE_STRING,
        )
    ],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_products_by_category(request, category):
    products = Products.objects.filter(category__iexact=category)
    if products.exists():
        serialized_products = ProductSerializer(products, many=True).data
        return Response({
            'category': category,
            'products': serialized_products
        }, status=200)
    else:
        return Response({
            'message': f"No products found in category '{category}'.",
            'category': category
        }, status=404)
    


@api_view(['GET'])
def api_categories(request):
    categories = Products.objects.values_list('category', flat=True).distinct()
    return Response({"categories": list(categories)})



from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from restaurant.models import All_Orders
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

@swagger_auto_schema(
    method='get',
    operation_description="View orders for the authenticated user",
    responses={
        200: openapi.Response('Successful operation', openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'order_no': openapi.Schema(type=openapi.TYPE_STRING),
                    'total': openapi.Schema(type=openapi.TYPE_STRING),
                    'date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                    'delivery_status': openapi.Schema(type=openapi.TYPE_STRING),
                    'restaurant': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'name': openapi.Schema(type=openapi.TYPE_STRING)
                        }
                    ),
                    'items': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'product_name': openapi.Schema(type=openapi.TYPE_STRING),
                                'quantity': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'price': openapi.Schema(type=openapi.TYPE_STRING),
                                'total': openapi.Schema(type=openapi.TYPE_STRING)
                            }
                        )
                    )
                }
            )
        )),
        404: openapi.Response('No orders found for this user')
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_view_orders(request):
    """
    View orders for the authenticated user.
    """
    user = request.user
    orders = All_Orders.objects.filter(user=user)

    if not orders:
        return Response({"error": "No orders found for this user."}, status=status.HTTP_404_NOT_FOUND)

    order_data = []
    for order in orders:
        order_items = []
        for order_item in order.orderitems_set.all():
            order_items.append({
                "product_name": order_item.product.product_name,
                "quantity": order_item.quantity,
                "price": str(order_item.price),
                "total": str(order_item.total)
            })
        
        order_data.append({
            "order_no": order.order_no,
            "total": str(order.total),
            "date": order.date,
            "delivery_status": order.delivery_status,
            "restaurant": {
                "id": order.restaurant.id,
                "name": order.restaurant.name
            },
            "items": order_items
        })

    return Response(order_data)



@swagger_auto_schema(
    method='get',
    operation_summary="View all products",
    operation_description="Retrieve a list of all products available in the system.",
    responses={
        200: openapi.Response(
            description="A list of products",
            examples={
                "application/json": [
                    {
                        "id": 1,
                        "product_name": "Burger",
                        "product_price": "5.99",
                        "category": "Food",
                        "description": "Delicious beef burger",
                        "restaurant": {
                            "id": 1,
                            "name": "Restaurant A"
                        },
                        "product_image": "http://example.com/path/to/image.jpg"
                    },
                    {
                        "id": 2,
                        "product_name": "Fries",
                        "product_price": "3.99",
                        "category": "Food",
                        "description": "Crispy fries",
                        "restaurant": {
                            "id": 1,
                            "name": "Restaurant A"
                        },
                        "product_image": "http://example.com/path/to/image2.jpg"
                    }
                ]
            }
        ),
        400: openapi.Response(
            description="Bad request",
            examples={"application/json": {"error": "Invalid request."}}
        )
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_view_products(request):
    """
    View all products in the system.
    """
    products = Products.objects.all()

    if not products:
        return Response({"error": "No products found."}, status=status.HTTP_404_NOT_FOUND)

    serialized_products = ProductSerializer(products, many=True).data

    return Response(serialized_products)

@swagger_auto_schema(
    methods=['get'],  
    operation_description="Retrieve a list of products for a specific restaurant based on its name.",
    responses={
        200: ProductSerializer(many=True),
        404: openapi.Response(description="Restaurant not found", schema=openapi.Schema(type=openapi.TYPE_OBJECT, properties={'detail': openapi.Schema(type=openapi.TYPE_STRING)})),
        500: openapi.Response(description="Internal server error")
    }
)
@api_view(['GET'])
@permission_classes([AllowAny])
def api_products_by_restaurant_view(request, restaurant_name):
    """
    View to list products of a specific restaurant by restaurant name.
    """
    # Get the restaurant object based on the name
    restaurant = get_object_or_404(Restaurant, name=restaurant_name)

    # Filter products based on the restaurant object
    products = Products.objects.filter(restaurant=restaurant)

    # Serialize the filtered products
    serialized_products = ProductSerializer(products, many=True)

    # Return the serialized data
    return Response(serialized_products.data)





@api_view(['GET'])
@permission_classes([AllowAny])
def api_view_product(request, product_name):
    """
    Retrieve a specific product by name, including its picture, price, and the restaurant it is found in.
    """
    try:
        product = Products.objects.get(product_name=product_name)
    except Products.DoesNotExist:
        return Response({"error": "Product not found."}, status=status.HTTP_404_NOT_FOUND)

    serializer = ProductSerializer(product)
    return Response(serializer.data)



@api_view(['PUT'])
@permission_classes([IsAdminUser])
def update_order_delivery_status(request, order_id):
    """
    View for admins to update the delivery status and remove completed orders
    """
    try:

        order = All_Orders.objects.get(id=order_id)
        new_status = request.data.get('delivery_status')

        if new_status:
            order.delivery_status = new_status
            order.save()
            if new_status == 'complete':
                order.delete()

            return Response({
                'message': 'Delivery status updated successfully',
                'order': AllOrdersSerializer(order).data
            }, status=status.HTTP_200_OK)

        return Response({"detail": "Delivery status not provided."}, status=status.HTTP_400_BAD_REQUEST)

    except All_Orders.DoesNotExist:
        raise NotFound(detail="Order not found")
    

@api_view(['GET'])
@permission_classes([IsAdminUser])
def api_all_orders(request):
    orders = All_Orders.objects.all()
    serialized_orders = AllOrdersSerializer(orders, many=True)
    return Response(serialized_orders.data)

#Donatello is a fellow



@csrf_exempt
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_delivery_status(request, order_no):
    try:
        order = All_Orders.objects.get(order_no=order_no)
    except All_Orders.DoesNotExist:
        return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = UpdateDeliveryStatusSerializer(order, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        if order.delivery_status == 'complete':  # Check if the status is 'complete'
            order.delete()  # Delete the order
            return Response({'message': 'Order completed and deleted.'}, status=status.HTTP_204_NO_CONTENT)
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.permissions import IsAuthenticated

@csrf_exempt
@swagger_auto_schema(
    method='patch',
    operation_description="Update the delivery status of an order",
    responses={
        200: openapi.Response('Successful operation', UpdateDeliveryStatusSerializer),
        204: openapi.Response('Order completed and deleted'),
        400: openapi.Response('Bad request'),
        404: openapi.Response('Order not found'),
    },
    request_body=UpdateDeliveryStatusSerializer
)
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_delivery_status(request, order_no):
    try:
        order = All_Orders.objects.get(order_no=order_no)
    except All_Orders.DoesNotExist:
        return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = UpdateDeliveryStatusSerializer(order, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        if order.delivery_status == 'complete':
            order.delete()  
            return Response({'message': 'Order completed and deleted.'}, status=status.HTTP_204_NO_CONTENT)
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .models import Restaurant, All_Orders
@api_view(['POST'])
def register_restaurant_owner(request):
    username = request.data.get('username')
    password = request.data.get('password')
    restaurant_name = request.data.get('restaurant_name')

    if User.objects.filter(username=username).exists():
        return JsonResponse({'error': 'Username already exists'}, status=400)

    user = User.objects.create_user(username=username, password=password)
    restaurant = Restaurant.objects.create(name=restaurant_name, user=user)
    return JsonResponse({'message': 'Restaurant owner registered successfully'}, status=201)

@api_view(['POST'])
def login_restaurant_owner(request):
    username = request.data.get('username')
    password = request.data.get('password')

    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)
        return JsonResponse({'message': 'Login successful'}, status=200)
    else:
        return JsonResponse({'error': 'Invalid credentials'}, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def view_orders(request):
    try:
        restaurant = Restaurant.objects.get(user=request.user)
        orders = Order.objects.filter(restaurant=restaurant)
        orders_data = [{'id': order.id, 'details': order.details} for order in orders]  # Adjust based on your Order model
        return JsonResponse({'orders': orders_data}, status=200)
    except Restaurant.DoesNotExist:
        return JsonResponse({'error': 'Restaurant not found'}, status=404)

from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Restaurant, All_Orders
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

@swagger_auto_schema(
    method='post',
    operation_description="Register a new restaurant owner",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'username': openapi.Schema(type=openapi.TYPE_STRING, description='Username of the restaurant owner'),
            'password': openapi.Schema(type=openapi.TYPE_STRING, description='Password of the restaurant owner'),
            'restaurant_name': openapi.Schema(type=openapi.TYPE_STRING, description='Name of the restaurant')
        }
    ),
    responses={
        201: openapi.Response('Restaurant owner registered successfully'),
        400: openapi.Response('Username already exists')
    }
)
@api_view(['POST'])
def register_restaurant_owner(request):
    username = request.data.get('username')
    password = request.data.get('password')
    restaurant_name = request.data.get('restaurant_name')

    if User.objects.filter(username=username).exists():
        return JsonResponse({'error': 'Username already exists'}, status=400)

    user = User.objects.create_user(username=username, password=password)
    restaurant = Restaurant.objects.create(name=restaurant_name, user=user)
    return JsonResponse({'message': 'Restaurant owner registered successfully'}, status=201)

@swagger_auto_schema(
    method='post',
    operation_description="Login a restaurant owner",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'username': openapi.Schema(type=openapi.TYPE_STRING, description='Username of the restaurant owner'),
            'password': openapi.Schema(type=openapi.TYPE_STRING, description='Password of the restaurant owner')
        }
    ),
    responses={
        200: openapi.Response('Login successful', openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'message': openapi.Schema(type=openapi.TYPE_STRING),
                'tokens': openapi.Schema(type=openapi.TYPE_OBJECT, properties={
                    'refresh': openapi.Schema(type=openapi.TYPE_STRING),
                    'access': openapi.Schema(type=openapi.TYPE_STRING)
                })
            }
        )),
        400: openapi.Response('Invalid credentials')
    }
)
@api_view(['POST'])
def login_restaurant_owner(request):
    username = request.data.get('username')
    password = request.data.get('password')

    user = authenticate(request, username=username, password=password)
    if user is not None:
        tokens = get_tokens_for_user(user)
        return JsonResponse({'message': 'Login successful', 'tokens': tokens}, status=200)
    else:
        return JsonResponse({'error': 'Invalid credentials'}, status=400)

@swagger_auto_schema(
    method='get',
    operation_description="View orders for the logged-in restaurant owner",
    responses={
        200: openapi.Response('Orders retrieved successfully', openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'orders': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_OBJECT, properties={
                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'order_no': openapi.Schema(type=openapi.TYPE_STRING),
                    'total': openapi.Schema(type=openapi.TYPE_NUMBER, format='decimal'),
                    'delivery_status': openapi.Schema(type=openapi.TYPE_STRING)
                }))
            }
        )),
        404: openapi.Response('Restaurant not found')
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def view_orders(request):
    try:
        restaurant = Restaurant.objects.get(user=request.user)
        orders = All_Orders.objects.filter(restaurant=restaurant)
        orders_data = [{'id': order.id, 'order_no': order.order_no, 'total': order.total, 'delivery_status': order.delivery_status} for order in orders]
        return JsonResponse({'orders': orders_data}, status=200)
    except Restaurant.DoesNotExist:
        return JsonResponse({'error': 'Restaurant not found'}, status=404)
