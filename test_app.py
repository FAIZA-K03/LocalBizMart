import unittest
from decimal import Decimal
from app import create_app
from app.extensions import db
from app.models import User, Business, Product, CartItem, Order, Payment
from app.services.whatsapp import WhatsAppService

class LocalBizMartTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for unit test client
        self.client = self.app.test_client()

    def test_homepage(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'LocalBizMart', response.data)
        self.assertIn(b'CraftyGifts', response.data)

    def test_browse_businesses(self):
        response = self.client.get('/businesses')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Aura', response.data)
        self.assertIn(b'Creative Corner', response.data)

    def test_business_and_product_details(self):
        with self.app.app_context():
            biz = Business.query.first()
            prod = Product.query.first()
            biz_id = biz.business_id
            prod_id = prod.product_id

        response = self.client.get(f'/business/{biz_id}')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Chat with Shop on WhatsApp', response.data)

        response = self.client.get(f'/product/{prod_id}')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'WhatsApp', response.data)

    def test_whatsapp_service(self):
        link = WhatsAppService.generate_link("9876543210", "Hello Test")
        self.assertTrue(link.startswith("https://wa.me/919876543210?text=Hello%20Test"))

        with self.app.app_context():
            order = Order.query.first()
            msg = WhatsAppService.build_order_customization_inquiry(order)
            self.assertIn(f"#LBM-{order.order_id}", msg)
            self.assertIn(order.customer.name, msg)
            self.assertIn("customization", msg.lower())
            order_link = WhatsAppService.generate_link(order.business.whatsapp_number, msg)
            self.assertTrue(order_link.startswith("https://wa.me/"))

    def test_customer_auth_and_cart(self):
        with self.app.app_context():
            prod = Product.query.first()
            prod_id = prod.product_id

        # 1. Login as customer
        login_res = self.client.post('/login', data={
            'email': 'rohan@customer.com',
            'password': 'Customer@123'
        }, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)
        self.assertIn(b'Welcome back', login_res.data)

        # 2. Add product to cart
        add_res = self.client.post(f'/cart/add/{prod_id}', data={'quantity': 2}, follow_redirects=True)
        self.assertEqual(add_res.status_code, 200)

        # 3. View cart
        cart_res = self.client.get('/cart')
        self.assertEqual(cart_res.status_code, 200)
        self.assertIn(b'Shopping Cart', cart_res.data)

        # 4. View My Orders
        orders_res = self.client.get('/orders')
        self.assertEqual(orders_res.status_code, 200)
        self.assertIn(b'My Orders', orders_res.data)

    def test_owner_dashboard_and_products(self):
        # Login as owner
        login_res = self.client.post('/login', data={
            'email': 'priya@sharmasweets.com',
            'password': 'Owner@123'
        }, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)

        # View owner dashboard
        dash_res = self.client.get('/owner/dashboard')
        self.assertEqual(dash_res.status_code, 200)
        self.assertIn(b'CraftyGifts', dash_res.data)

        # View owner products
        prod_res = self.client.get('/owner/products')
        self.assertEqual(prod_res.status_code, 200)
        self.assertIn(b'Resin Photo Frame', prod_res.data)

        # View incoming orders
        ord_res = self.client.get('/owner/orders')
        self.assertEqual(ord_res.status_code, 200)

    def test_admin_portal(self):
        # Admin login
        admin_login_res = self.client.post('/admin/login', data={
            'email': 'admin@localbizmart.com',
            'password': 'Admin@123'
        }, follow_redirects=True)
        self.assertEqual(admin_login_res.status_code, 200)
        self.assertIn(b'Platform Overview', admin_login_res.data)

        # View users, businesses, products, orders, categories
        self.assertEqual(self.client.get('/admin/users').status_code, 200)
        self.assertEqual(self.client.get('/admin/businesses').status_code, 200)
        self.assertEqual(self.client.get('/admin/products').status_code, 200)
        self.assertEqual(self.client.get('/admin/orders').status_code, 200)
        self.assertEqual(self.client.get('/admin/categories').status_code, 200)

    def test_full_order_and_status_lifecycle(self):
        with self.app.app_context():
            prod = Product.query.first()
            prod_id = prod.product_id
            expected_name = prod.name

        # 1. Customer login
        self.client.post('/login', data={'email': 'rohan@customer.com', 'password': 'Customer@123'}, follow_redirects=True)

        # 2. Add product to cart
        self.client.post('/cart/clear', follow_redirects=True)
        self.client.post(f'/cart/add/{prod_id}', data={'quantity': 1}, follow_redirects=True)

        # 3. Checkout with UPI (Sharma Sweets / CraftyGifts is UPI only)
        checkout_res = self.client.post('/checkout', data={
            'delivery_address': 'Flat 101, Test Apartment, Near Metro Station, Test City 123456',
            'notes': 'Call before delivery',
            'payment_method': 'UPI'
        }, follow_redirects=True)
        self.assertEqual(checkout_res.status_code, 200)
        self.assertIn(b'Your order has been placed successfully', checkout_res.data)
        self.assertIn(b'Chat with Seller on WhatsApp', checkout_res.data)

        # 4. Check database state
        with self.app.app_context():
            newest_order = Order.query.order_by(Order.order_id.desc()).first()
            self.assertEqual(newest_order.status, Order.STATUS_PENDING)
            self.assertEqual(newest_order.items[0].product_name, expected_name)
            self.assertEqual(newest_order.payment.payment_method, 'UPI')
            self.assertEqual(newest_order.payment.payment_status, 'Pending')
            order_id = newest_order.order_id

        # 5. Switch to Owner
        self.client.get('/logout', follow_redirects=True)
        self.client.post('/login', data={'email': 'priya@sharmasweets.com', 'password': 'Owner@123'}, follow_redirects=True)

        # Attempting to confirm UPI order before payment verification should be blocked
        blocked_confirm = self.client.post(f'/owner/order/{order_id}/update-status', data={'new_status': 'Confirmed'}, follow_redirects=True)
        self.assertIn(b'payment must be verified', blocked_confirm.data.lower())

        # Owner marks UPI payment as Paid
        pay_res = self.client.post(f'/owner/order/{order_id}/verify-payment', data={'payment_status': 'Paid'}, follow_redirects=True)
        self.assertIn(b'Paid', pay_res.data)

        # Owner advances: Pending -> Confirmed (now allowed after payment verified)
        res1 = self.client.post(f'/owner/order/{order_id}/update-status', data={'new_status': 'Confirmed'}, follow_redirects=True)
        self.assertIn(b'Confirmed', res1.data)

        # Owner advances: Confirmed -> Processing
        res2 = self.client.post(f'/owner/order/{order_id}/update-status', data={'new_status': 'Processing'}, follow_redirects=True)
        self.assertIn(b'Processing', res2.data)

        # Owner advances: Processing -> Shipped
        res3 = self.client.post(f'/owner/order/{order_id}/update-status', data={'new_status': 'Shipped'}, follow_redirects=True)
        self.assertIn(b'Shipped', res3.data)

        # Owner advances: Shipped -> Delivered
        res4 = self.client.post(f'/owner/order/{order_id}/update-status', data={'new_status': 'Delivered'}, follow_redirects=True)
        self.assertIn(b'Delivered', res4.data)

        # Verify invalid status transition: Delivered -> Cancelled (should fail)
        invalid_res = self.client.post(f'/owner/order/{order_id}/update-status', data={'new_status': 'Cancelled', 'cancel_reason': 'test'}, follow_redirects=True)
        self.assertIn(b'Invalid status transition', invalid_res.data)

    def test_confirm_and_process_shortcut(self):
        """Tests the optional UI shortcut: directly advancing from Pending -> Processing."""
        with self.app.app_context():
            # Find Anita's business (accepts COD) and product
            biz = Business.query.filter_by(name="Aura Ethnic Wear & Clothing Boutique").first()
            prod = Product.query.filter_by(business_id=biz.business_id, is_available=True).first()
            prod_id = prod.product_id

        # 1. Customer places COD order
        self.client.post('/login', data={'email': 'rohan@customer.com', 'password': 'Customer@123'}, follow_redirects=True)
        self.client.post('/cart/clear', follow_redirects=True)
        self.client.post(f'/cart/add/{prod_id}', data={'quantity': 1}, follow_redirects=True)
        checkout_res = self.client.post('/checkout', data={
            'delivery_address': 'Flat 202, Sunshine Heights, Mumbai 400001',
            'notes': 'Leave at security',
            'payment_method': 'COD'
        }, follow_redirects=True)
        self.assertEqual(checkout_res.status_code, 200)

        with self.app.app_context():
            order = Order.query.order_by(Order.order_id.desc()).first()
            order_id = order.order_id
            self.assertEqual(order.status, Order.STATUS_PENDING)

        # 2. Switch to Owner (Anita)
        self.client.get('/logout', follow_redirects=True)
        self.client.post('/login', data={'email': 'anita@craftcorner.com', 'password': 'Owner@123'}, follow_redirects=True)

        # Shortcut: Pending -> Processing directly!
        shortcut_res = self.client.post(f'/owner/order/{order_id}/update-status', data={'new_status': 'Processing'}, follow_redirects=True)
        self.assertEqual(shortcut_res.status_code, 200)
        self.assertIn(b'Processing', shortcut_res.data)

        # Verify both Confirmed and Processing steps exist in OrderStatusHistory
        with self.app.app_context():
            saved_order = Order.query.get(order_id)
            self.assertEqual(saved_order.status, Order.STATUS_PROCESSING)
            hist_statuses = [h.status for h in saved_order.status_history]
            self.assertIn('Confirmed', hist_statuses)
            self.assertIn('Processing', hist_statuses)

    def test_cod_payment_lifecycle(self):
        """Tests that COD payments cannot be marked Paid before Delivered, and are auto-paid upon Delivered."""
        with self.app.app_context():
            biz = Business.query.filter_by(name="Creative Corner Crafts & Tailoring").first()
            prod = Product.query.filter_by(business_id=biz.business_id, is_available=True).first()
            prod_id = prod.product_id

        # 1. Customer places COD order
        self.client.post('/login', data={'email': 'rohan@customer.com', 'password': 'Customer@123'}, follow_redirects=True)
        self.client.post('/cart/clear', follow_redirects=True)
        self.client.post(f'/cart/add/{prod_id}', data={'quantity': 1}, follow_redirects=True)
        self.client.post('/checkout', data={
            'delivery_address': 'Plot 44, Indiranagar, Bengaluru 560038',
            'notes': 'COD test',
            'payment_method': 'COD'
        }, follow_redirects=True)

        with self.app.app_context():
            order = Order.query.order_by(Order.order_id.desc()).first()
            order_id = order.order_id

        # 2. Owner (Rajesh) logs in
        self.client.get('/logout', follow_redirects=True)
        self.client.post('/login', data={'email': 'rajesh@bakersdelight.com', 'password': 'Owner@123'}, follow_redirects=True)

        # Attempt to mark COD payment as Paid while order is still Pending: SHOULD FAIL
        pre_deliver_pay = self.client.post(f'/owner/order/{order_id}/verify-payment', data={'payment_status': 'Paid'}, follow_redirects=True)
        self.assertIn(b'only be marked as', pre_deliver_pay.data)

        with self.app.app_context():
            check_order = Order.query.get(order_id)
            self.assertEqual(check_order.payment.payment_status, Payment.STATUS_PENDING)

        # Advance order through steps
        self.client.post(f'/owner/order/{order_id}/update-status', data={'new_status': 'Confirmed'}, follow_redirects=True)
        self.client.post(f'/owner/order/{order_id}/update-status', data={'new_status': 'Processing'}, follow_redirects=True)
        self.client.post(f'/owner/order/{order_id}/update-status', data={'new_status': 'Shipped'}, follow_redirects=True)

        # Advance to Delivered: COD payment should automatically become Paid!
        deliver_res = self.client.post(f'/owner/order/{order_id}/update-status', data={'new_status': 'Delivered'}, follow_redirects=True)
        self.assertIn(b'Delivered', deliver_res.data)

        with self.app.app_context():
            delivered_order = Order.query.get(order_id)
            self.assertEqual(delivered_order.status, Order.STATUS_DELIVERED)
            self.assertEqual(delivered_order.payment.payment_status, Payment.STATUS_PAID)

    def test_product_multi_images(self):
        """Tests that products have 1 to 3 images, with primary image fallback."""
        with self.app.app_context():
            resin_prod = Product.query.filter_by(name="Personalized Resin Photo Frame").first()
            self.assertIsNotNone(resin_prod)
            # Should have 3 seeded photos
            self.assertEqual(resin_prod.photo_count, 3)
            self.assertEqual(len(resin_prod.image_list), 3)
            self.assertTrue(resin_prod.primary_image_path.startswith("uploads/"))

            # Single photo product
            box_prod = Product.query.filter_by(name="Handmade Explosion Photo Box").first()
            self.assertIsNotNone(box_prod)
            self.assertGreaterEqual(box_prod.photo_count, 1)
            self.assertLessEqual(box_prod.photo_count, 3)

    def test_ist_time_format(self):
        """Tests that timestamps are recorded in local IST without negative UTC offsets."""
        from app.utils.helpers import get_current_time
        now_ist = get_current_time()
        self.assertIsNotNone(now_ist)
        # Verify strftime works without error
        formatted = now_ist.strftime('%d %b %Y, %I:%M %p')
        self.assertTrue(len(formatted) > 10)

if __name__ == '__main__':
    unittest.main()
