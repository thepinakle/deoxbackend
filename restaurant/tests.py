from django.test import TestCase, Client
from django.contrib.auth.models import User
from .models import Cart, OrderItems, Products, Restaurant

class CartTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.client.login(username='testuser', password='12345')
        self.restaurant = Restaurant.objects.create(name='Test Restaurant', user=self.user)
        self.product = Products.objects.create(
            product_image='path/to/image.jpg',  # Provide a valid image path
            product_name='Test Product',
            product_price=10.00,
            category='Test Category',
            description='Test Description',
            restaurant=self.restaurant  # Use the created restaurant instance
        )
        self.cart = Cart.objects.create(user=self.user)
        self.order_item = OrderItems.objects.create(cart=self.cart, product=self.product, quantity=1, price=10.00)

    def test_view_cart(self):
        response = self.client.get('/cart/view/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Test Product', response.content.decode())

    def test_remove_from_cart(self):
        response = self.client.delete(f'/cart/remove/{self.order_item.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(OrderItems.objects.count(), 0)
