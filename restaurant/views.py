import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from rest_framework.permissions import IsAuthenticated
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
from rest_framework import serializers
from .models import Restaurant, Products
from .serializers import RestaurantSerializer, ProductSerializer
from rest_framework.permissions import IsAdminUser


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
        data = json.loads(request.body)
        product_id = data['product_id']
        quantity = data['quantity']

        product = get_object_or_404(Products, id=product_id)
        cart_item, created = Cart.objects.get_or_create(user=request.user, product=product)
        if not created:
            cart_item.quantity += quantity
        else:
            cart_item.quantity = quantity
        cart_item.save()

        return JsonResponse({'message': 'Item added to cart', 'cart_item_id': cart_item.id})
    except json.JSONDecodeError:
        logger.error("Invalid JSON payload")
        return JsonResponse({'error': 'Invalid JSON payload'}, status=400)
    except KeyError as e:
        logger.error(f"Missing key in request payload: {e}")
        return JsonResponse({'error': f"Missing key: {e}"}, status=400)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return JsonResponse({'error': 'An unexpected error occurred'}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_order(request):
    try:
        data = json.loads(request.body)
        logger.info(f"Request payload: {data}")
        
        hostel_name = data['hostel_name']
        block_number = data['block_number']
        room_number = data['room_number']
        phone_number = format_phone_number(data['phone_number'])

        cart_items = Cart.objects.filter(user=request.user)
        if not cart_items.exists():
            return JsonResponse({'error': 'Cart is empty'}, status=400)

        total_amount = sum(item.total for item in cart_items)

        # Generate a unique order number
        order_no = f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"

        order = All_Orders.objects.create(
            user=request.user,
            total=total_amount,
            hostel_name=hostel_name,
            block_number=block_number,
            room_number=room_number,
            mobile=phone_number,
            order_no=order_no  # Set the generated order number
        )

        for item in cart_items:
            OrderItems.objects.create(order=order, product=item.product, quantity=item.quantity, price=item.price)
            item.delete()  # Remove item from cart after adding to order

        # Initiate M-Pesa payment
        transaction_desc = f"Payment for order {order.order_no}"
        account_reference = f"Order {order.order_no}"
        response = lipa_na_mpesa_online(phone_number, total_amount, account_reference, transaction_desc)

        if 'errorCode' in response:
            return JsonResponse({'error': response['errorMessage'], 'mpesa_response': response}, status=400)

        Payments.objects.create(
            user=request.user,
            mobile=phone_number,
            amount=total_amount,
            payments_status=False,
            mpesa_receipt_number='',
            mpesa_transaction_date=None
        )

        return JsonResponse({'message': 'Order created and payment initiated', 'order_id': order.id, 'mpesa_response': response})
    except json.JSONDecodeError:
        logger.error("Invalid JSON payload")
        return JsonResponse({'error': 'Invalid JSON payload'}, status=400)
    except KeyError as e:
        logger.error(f"Missing key in request payload: {e}")
        return JsonResponse({'error': f"Missing key: {e}"}, status=400)
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
    return JsonResponse({'status': 'success', 'message': 'Item removed from cart'})

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

@swagger_auto_schema(
    method='get',
    operation_summary="View orders for the authenticated user",
    operation_description="Retrieve all orders associated with the currently authenticated user.",
    responses={
        200: openapi.Response(
            description="A list of orders for the authenticated user",
            examples={
                "application/json": [
                    {
                        "order_no": "ORD12345",
                        "total": "29.99",
                        "date": "2025-01-08T12:34:56",
                        "delivery_status": "on_transit",
                        "restaurant": {
                            "id": 1,
                            "name": "Restaurant A"
                        },
                        "items": [
                            {
                                "product_name": "Burger",
                                "quantity": 2,
                                "price": "5.99",
                                "total": "11.98"
                            },
                            {
                                "product_name": "Fries",
                                "quantity": 1,
                                "price": "3.99",
                                "total": "3.99"
                            }
                        ]
                    }
                ]
            }
        ),
        401: openapi.Response(
            description="Unauthorized access",
            examples={"application/json": {"error": "Authentication credentials were not provided."}}
        )
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

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Products
from .serializers import ProductSerializer

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_products_by_restaurant_view(request, restaurant_id):
    """
    View to list products of a specific restaurant by restaurant ID
    """
    try:
        # Filter products based on the restaurant id
        products = Products.objects.filter(restaurant__id=restaurant_id)

        # Serialize the filtered products
        serialized_products = ProductSerializer(products, many=True)

        # Return the serialized data
        return Response(serialized_products.data)

    except Products.DoesNotExist:
        # Handle the case where the restaurant has no products
        return Response({"detail": "Products not found for this restaurant"}, status=404)


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
