import os
from decimal import Decimal
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont

from app import create_app
from app.extensions import db
from app.models import (
    User, Category, Business, Product, ProductImage,
    Order, OrderItem, OrderStatusHistory,
    BusinessPaymentSettings, Payment
)
from app.utils.helpers import get_current_time

def create_sample_image(filename: str, title: str, bg_color: tuple, text_color: tuple = (255, 255, 255)):
    """Creates a clean sample product image for demo purposes."""
    uploads_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app', 'static', 'uploads')
    os.makedirs(uploads_dir, exist_ok=True)
    file_path = os.path.join(uploads_dir, filename)

    img = Image.new('RGB', (500, 350), color=bg_color)
    draw = ImageDraw.Draw(img)

    # Simple border and product label
    draw.rectangle([15, 15, 485, 335], outline=(255, 255, 255), width=2)
    draw.text((250, 160), title, fill=text_color, anchor="mm")
    draw.text((250, 195), "LocalBizMart Seller Item", fill=(240, 240, 240), anchor="mm")

    img.save(file_path, "PNG")
    return f"uploads/{filename}"


def seed_database(app=None):
    if app is None:
        app = create_app()

    with app.app_context():
        print("Initializing LocalBizMart database...")
        db.create_all()

        print("Clearing old records...")
        Payment.query.delete()
        OrderStatusHistory.query.delete()
        OrderItem.query.delete()
        Order.query.delete()
        ProductImage.query.delete()
        Product.query.delete()
        BusinessPaymentSettings.query.delete()
        Business.query.delete()
        Category.query.delete()
        User.query.delete()
        db.session.commit()

        # -------------------------------------------------------------
        # 1. Admin Account
        # -------------------------------------------------------------
        print("1. Creating Administrator account...")
        admin = User(
            name="Platform Administrator",
            email="admin@localbizmart.com",
            phone="9000000000",
            role="admin",
            status="active"
        )
        admin.set_password("Admin@123")
        db.session.add(admin)

        # -------------------------------------------------------------
        # 2. Categories (Diverse: Gifting, Clothing, Crafts, Tailoring, etc.)
        # -------------------------------------------------------------
        print("2. Creating Categories...")
        category_names = [
            "Gifting & Hampers",
            "Boutique & Clothing",
            "Handicrafts & Decor",
            "Tailoring",
            "Bakery & Treats",
            "Grocery/Stationery",
            "Food"
        ]
        categories = {}
        for name in category_names:
            cat = Category(category_name=name)
            db.session.add(cat)
            categories[name] = cat

        db.session.flush()

        # -------------------------------------------------------------
        # 3. Generate Sample Images for Diverse Products
        # -------------------------------------------------------------
        print("3. Generating sample product preview images (1 to 3 photos per product)...")
        # Gifting images (multiple angles/details)
        img_resin = create_sample_image("gift_resin_frame.png", "Custom Resin Frame - Main", (190, 75, 95))
        img_resin_2 = create_sample_image("gift_resin_frame_2.png", "Floral Details & Gold Foil", (205, 85, 105))
        img_resin_3 = create_sample_image("gift_resin_frame_3.png", "Resin Frame Gift Packaging", (175, 65, 85))

        img_hamper = create_sample_image("gift_birthday_hamper.png", "Birthday Celebration Hamper", (124, 58, 237))
        img_hamper_2 = create_sample_image("gift_birthday_hamper_2.png", "Custom Mug & Scented Candle", (138, 70, 245))
        img_hamper_3 = create_sample_image("gift_birthday_hamper_3.png", "Artisan Chocolates & Teddy", (110, 45, 215))

        img_keychain = create_sample_image("gift_wooden_keychain.png", "Engraved Keychain", (180, 83, 9))
        img_box = create_sample_image("gift_explosion_box.png", "Handmade Photo Box", (225, 29, 72))
        img_basket = create_sample_image("gift_festival_basket.png", "Festival Gift Basket", (161, 98, 7))

        # Clothing & Boutique images
        img_kurti = create_sample_image("cloth_cotton_kurti.png", "Handblock Pure Cotton Kurti", (14, 116, 144))
        img_kurti_2 = create_sample_image("cloth_cotton_kurti_2.png", "Jaipur Handblock Print Motif", (24, 136, 164))
        img_kurti_3 = create_sample_image("cloth_cotton_kurti_3.png", "Kurti Neck & Wooden Buttons", (10, 96, 124))

        img_dupatta = create_sample_image("cloth_dupatta.png", "Embroidered Dupatta", (15, 118, 110))
        img_dress = create_sample_image("cloth_summer_dress.png", "Floral Summer Dress", (4, 120, 87))
        img_anarkali = create_sample_image("cloth_anarkali_set.png", "Festive Kurta Set", (159, 18, 57))
        img_shirt = create_sample_image("cloth_khadi_shirt.png", "Khadi Casual Shirt", (51, 65, 85))

        # Handicrafts & Tailoring images
        img_macrame = create_sample_image("craft_macrame_wall.png", "Macrame Wall Hanging", (180, 83, 9))
        img_macrame_2 = create_sample_image("craft_macrame_wall_2.png", "Cotton Knots & Driftwood Detail", (195, 95, 18))
        img_candle = create_sample_image("craft_scented_candle.png", "Soy Scented Candle", (139, 92, 246))
        img_planters = create_sample_image("craft_terracotta_pots.png", "Hand-Painted Planters", (194, 65, 12))
        img_tailoring = create_sample_image("craft_custom_tailoring.png", "Custom Blouse Stitching", (217, 70, 239))

        # Bakery & Custom Cakes images (Baker King)
        img_truffle = create_sample_image("cake_chocolate_truffle.png", "Chocolate Truffle Cake", (75, 40, 25))
        img_truffle_2 = create_sample_image("cake_chocolate_truffle_2.png", "Rich Truffle Ganache & Curls", (95, 50, 30))
        img_truffle_3 = create_sample_image("cake_chocolate_truffle_3.png", "Baker King Custom Box", (60, 30, 18))

        img_pineapple = create_sample_image("cake_pineapple.png", "Fresh Pineapple Cake", (215, 155, 20))
        img_pineapple_2 = create_sample_image("cake_pineapple_2.png", "Fresh Pineapple Chunks & Cream", (235, 175, 35))

        # Payment Receipts
        receipt_1 = create_sample_image("receipt_sample_1.png", "UPI Payment Receipt", (16, 185, 129))
        receipt_3 = create_sample_image("receipt_sample_3.png", "UPI Receipt Screenshot", (79, 70, 229))

        # -------------------------------------------------------------
        # 4. Business 1: Gifting Business (Priya Sen - UPI Only)
        # -------------------------------------------------------------
        print("4. Creating Business 1: CraftyGifts Studio (Gifting Brand)...")
        owner1 = User(
            name="Priya Sen",
            email="priya@sharmasweets.com",  # Kept email for login backwards-compatibility
            phone="9876543210",
            role="owner",
            status="active"
        )
        owner1.set_password("Owner@123")
        db.session.add(owner1)
        db.session.flush()

        biz1 = Business(
            owner_id=owner1.user_id,
            name="CraftyGifts & Customized Hampers",
            description="Personalized gift hampers, custom resin frames, explosion boxes, and curated celebration presents for birthdays, anniversaries, and corporate events.",
            category_id=categories["Gifting & Hampers"].category_id,
            address="Studio 14, Lotus Apartment, Near Navrang Circle, Ahmedabad - 380009",
            whatsapp_number="9876543210",
            status="active"
        )
        db.session.add(biz1)
        db.session.flush()

        pay1 = BusinessPaymentSettings(
            business_id=biz1.business_id,
            accepts_upi=True,
            upi_id="craftygifts@okhdfcbank",
            accepts_cod=False
        )
        db.session.add(pay1)

        p1_1 = Product(business_id=biz1.business_id, name="Personalized Resin Photo Frame", description="Handmade floral preserved resin frame customized with your photograph and golden foil letters.", price=Decimal("499.00"), image_path=img_resin, is_available=True)
        p1_2 = Product(business_id=biz1.business_id, name="Curated Birthday Celebration Hamper", description="Includes personalized mug, scented candle, mini teddy, artisan chocolates, and handwritten card.", price=Decimal("850.00"), image_path=img_hamper, is_available=True)
        p1_3 = Product(business_id=biz1.business_id, name="Custom Engraved Wooden Keychain (Pair)", description="Polished teakwood keychains with names or coordinates engraved on both sides.", price=Decimal("220.00"), image_path=img_keychain, is_available=True)
        p1_4 = Product(business_id=biz1.business_id, name="Handmade Explosion Photo Box", description="Multi-layered memory box with pop-up photo slots and central chocolate holder.", price=Decimal("550.00"), image_path=img_box, is_available=True)
        p1_5 = Product(business_id=biz1.business_id, name="Festive Treats & Candle Basket", description="Special festival basket with handcrafted brass diya and soy candle in a reusable cane basket.", price=Decimal("750.00"), image_path=img_basket, is_available=False) # Unavailable
        db.session.add_all([p1_1, p1_2, p1_3, p1_4, p1_5])

        # -------------------------------------------------------------
        # 5. Business 2: Clothing Brand & Boutique (Anita Desai - UPI & COD)
        # -------------------------------------------------------------
        print("5. Creating Business 2: Aura Ethnic Wear & Boutique (Clothing Brand)...")
        owner2 = User(
            name="Anam Fatima",
            email="urbanclothing@gmail.com",
            phone="9876543211",
            role="owner",
            status="active"
        )
        owner2.set_password("Owner@123")
        db.session.add(owner2)
        db.session.flush()

        biz2 = Business(
            owner_id=owner2.user_id,
            name="Urban Clothing",
            description="Hand-block printed cotton kurtis, customized festive ethnic sets, comfortable summer dresses, and artisanal dupattas tailored with love.",
            category_id=categories["Boutique & Clothing"].category_id,
            address="Shop 5, Fashion Street Lane, Kalaghoda, Mumbai - 400001",
            whatsapp_number="9876543211",
            status="active"
        )
        db.session.add(biz2)
        db.session.flush()

        pay2 = BusinessPaymentSettings(
            business_id=biz2.business_id,
            accepts_upi=True,
            upi_id="urbanclothing@ubin",
            accepts_cod=True
        )
        db.session.add(pay2)

        p2_1 = Product(business_id=biz2.business_id, name="Handblock Printed Pure Cotton Kurti", description="100% breathable cotton kurti with traditional Jaipur handblock prints and wooden button details.", price=Decimal("699.00"), image_path=img_kurti, is_available=True)
        p2_2 = Product(business_id=biz2.business_id, name="Designer Embroidered Chanderi Dupatta", description="Lightweight festive dupatta featuring fine zari border and delicate floral embroidery.", price=Decimal("450.00"), image_path=img_dupatta, is_available=True)
        p2_3 = Product(business_id=biz2.business_id, name="Floral Casual Summer Dress", description="Soft cotton tiered midi dress with adjustable waist tie, perfect for casual outings.", price=Decimal("899.00"), image_path=img_dress, is_available=True)
        p2_4 = Product(business_id=biz2.business_id, name="Festive Anarkali Kurta Set with Pants", description="3-piece elegant anarkali set with matching cigarette pants and chiffon dupatta.", price=Decimal("1250.00"), image_path=img_anarkali, is_available=True)
        p2_5 = Product(business_id=biz2.business_id, name="Hand-woven Khadi Casual Shirt", description="Natural dyed khadi unisex relaxed fit shirt with mandarin collar.", price=Decimal("599.00"), image_path=img_shirt, is_available=False) # Unavailable
        db.session.add_all([p2_1, p2_2, p2_3, p2_4, p2_5])

        # -------------------------------------------------------------
        # 6. Business 3: Handmade Decor & Tailoring (Rajesh Kumar - COD Only)
        # -------------------------------------------------------------
        print("6. Creating Business 3: Creative Corner Crafts & Tailoring...")
        owner3 = User(
            name="Rajesh Kumar",
            email="rajesh@bakersdelight.com",
            phone="9876543212",
            role="owner",
            status="active"
        )
        owner3.set_password("Owner@123")
        db.session.add(owner3)
        db.session.flush()

        biz3 = Business(
            owner_id=owner3.user_id,
            name="Creative Corner Crafts & Tailoring",
            description="Handmade home decor, boho macrame wall hangings, natural scented candles, and custom boutique stitching services.",
            category_id=categories["Handicrafts & Decor"].category_id,
            address="House 8, 2nd Main, Green Glen Layout, Bellandur, Bengaluru - 560103",
            whatsapp_number="9876543212",
            status="active"
        )
        db.session.add(biz3)
        db.session.flush()

        pay3 = BusinessPaymentSettings(
            business_id=biz3.business_id,
            accepts_upi=False,
            upi_id=None,
            accepts_cod=True
        )
        db.session.add(pay3)

        p3_1 = Product(business_id=biz3.business_id, name="Boho Macrame Wall Hanging Tapestry", description="Hand-knotted 100% natural cotton macrame cord suspended on a smooth driftwood branch.", price=Decimal("799.00"), image_path=img_macrame, is_available=True)
        p3_2 = Product(business_id=biz3.business_id, name="Handcrafted Lavender Soy Scented Candle", description="Non-toxic eco-friendly soy candle infused with calming lavender essential oils (30 hr burn time).", price=Decimal("320.00"), image_path=img_candle, is_available=True)
        p3_3 = Product(business_id=biz3.business_id, name="Hand-Painted Terracotta Planters (Set of 2)", description="Clay planters painted with traditional Warli art and sealed with waterproof varnish.", price=Decimal("599.00"), image_path=img_planters, is_available=True)
        p3_4 = Product(business_id=biz3.business_id, name="Custom Saree Blouse Tailoring Service", description="Tailoring and alteration service with custom neckline, cups, and piping based on your measurements.", price=Decimal("450.00"), image_path=img_tailoring, is_available=True)
        db.session.add_all([p3_1, p3_2, p3_3, p3_4])
        db.session.flush()

        # Attach multi-photo ProductImage records (1 to 3 photos per product)
        def attach_photos(prod, paths):
            for i, p in enumerate(paths):
                pi = ProductImage(product_id=prod.product_id, image_path=p, is_primary=(i == 0), display_order=i)
                db.session.add(pi)

        # Gifting products (Hero items have 3 photos)
        attach_photos(p1_1, [img_resin, img_resin_2, img_resin_3])
        attach_photos(p1_2, [img_hamper, img_hamper_2, img_hamper_3])
        attach_photos(p1_3, [img_keychain])
        attach_photos(p1_4, [img_box])
        attach_photos(p1_5, [img_basket])

        # Clothing products (Hero items have 3 photos)
        attach_photos(p2_1, [img_kurti, img_kurti_2, img_kurti_3])
        attach_photos(p2_2, [img_dupatta])
        attach_photos(p2_3, [img_dress])
        attach_photos(p2_4, [img_anarkali])
        attach_photos(p2_5, [img_shirt])

        # Crafts products
        attach_photos(p3_1, [img_macrame, img_macrame_2])
        attach_photos(p3_2, [img_candle])
        attach_photos(p3_3, [img_planters])
        attach_photos(p3_4, [img_tailoring])

        # -------------------------------------------------------------
        # 7. Demo Customers
        # -------------------------------------------------------------
        print("7. Creating demo Customer accounts...")
        customer1 = User(
            name="Rohan Gupta",
            email="rohan@customer.com",
            phone="9811122233",
            role="customer",
            status="active"
        )
        customer1.set_password("Customer@123")

        customer2 = User(
            name="Sneha Patel",
            email="sneha@customer.com",
            phone="9822233344",
            role="customer",
            status="active"
        )
        customer2.set_password("Customer@123")

        db.session.add_all([customer1, customer2])
        db.session.flush()

        # -------------------------------------------------------------
        # 8. Sample Orders in Diverse Statuses
        # -------------------------------------------------------------
        print("8. Creating sample orders in different statuses...")
        now = get_current_time()

        # Order 1: Rohan -> CraftyGifts: Delivered (UPI Paid with screenshot)
        order1 = Order(
            customer_id=customer1.user_id,
            business_id=biz1.business_id,
            total_amount=Decimal("719.00"),
            status=Order.STATUS_DELIVERED,
            delivery_address="B-301, Silver Oak Residency, SG Highway, Ahmedabad - 380054",
            notes="Please pack carefully in gift wrap with a red ribbon.",
            placed_at=now - timedelta(days=3, hours=4)
        )
        db.session.add(order1)
        db.session.flush()

        item1_1 = OrderItem(order_id=order1.order_id, product_id=p1_1.product_id, product_name=p1_1.name, quantity=1, unit_price=Decimal("499.00"))
        item1_2 = OrderItem(order_id=order1.order_id, product_id=p1_3.product_id, product_name=p1_3.name, quantity=1, unit_price=Decimal("220.00"))
        db.session.add_all([item1_1, item1_2])

        hist1_1 = OrderStatusHistory(order_id=order1.order_id, status=Order.STATUS_PENDING, changed_at=now - timedelta(days=3, hours=4), reason="Order placed by customer on LocalBizMart.")
        hist1_2 = OrderStatusHistory(order_id=order1.order_id, status=Order.STATUS_CONFIRMED, changed_at=now - timedelta(days=3, hours=2), reason="Status updated from Pending to Confirmed by seller.")
        hist1_3 = OrderStatusHistory(order_id=order1.order_id, status=Order.STATUS_PROCESSING, changed_at=now - timedelta(days=2, hours=10), reason="Status updated from Confirmed to Processing by seller.")
        hist1_4 = OrderStatusHistory(order_id=order1.order_id, status=Order.STATUS_SHIPPED, changed_at=now - timedelta(days=1, hours=8), reason="Status updated from Processing to Shipped by seller.")
        hist1_5 = OrderStatusHistory(order_id=order1.order_id, status=Order.STATUS_DELIVERED, changed_at=now - timedelta(hours=6), reason="Status updated from Shipped to Delivered by seller.")
        db.session.add_all([hist1_1, hist1_2, hist1_3, hist1_4, hist1_5])

        pay1_rec = Payment(
            order_id=order1.order_id,
            payment_method=Payment.METHOD_UPI,
            payment_status=Payment.STATUS_PAID,
            screenshot_path=receipt_1,
            updated_at=now - timedelta(days=3, hours=1)
        )
        db.session.add(pay1_rec)

        # Order 2: Rohan -> Creative Corner: Shipped (COD, Payment Pending)
        order2 = Order(
            customer_id=customer1.user_id,
            business_id=biz3.business_id,
            total_amount=Decimal("1119.00"),
            status=Order.STATUS_SHIPPED,
            delivery_address="B-301, Silver Oak Residency, SG Highway, Ahmedabad - 380054",
            notes="Please call before reaching destination.",
            placed_at=now - timedelta(days=1, hours=2)
        )
        db.session.add(order2)
        db.session.flush()

        item2_1 = OrderItem(order_id=order2.order_id, product_id=p3_1.product_id, product_name=p3_1.name, quantity=1, unit_price=Decimal("799.00"))
        item2_2 = OrderItem(order_id=order2.order_id, product_id=p3_2.product_id, product_name=p3_2.name, quantity=1, unit_price=Decimal("320.00"))
        db.session.add_all([item2_1, item2_2])

        hist2_1 = OrderStatusHistory(order_id=order2.order_id, status=Order.STATUS_PENDING, changed_at=now - timedelta(days=1, hours=2), reason="Order placed by customer.")
        hist2_2 = OrderStatusHistory(order_id=order2.order_id, status=Order.STATUS_CONFIRMED, changed_at=now - timedelta(days=1), reason="Status updated to Confirmed by seller.")
        hist2_3 = OrderStatusHistory(order_id=order2.order_id, status=Order.STATUS_PROCESSING, changed_at=now - timedelta(hours=14), reason="Status updated to Processing by seller.")
        hist2_4 = OrderStatusHistory(order_id=order2.order_id, status=Order.STATUS_SHIPPED, changed_at=now - timedelta(hours=3), reason="Status updated to Shipped by seller.")
        db.session.add_all([hist2_1, hist2_2, hist2_3, hist2_4])

        pay2_rec = Payment(
            order_id=order2.order_id,
            payment_method=Payment.METHOD_COD,
            payment_status=Payment.STATUS_PENDING,
            updated_at=now - timedelta(days=1, hours=2)
        )
        db.session.add(pay2_rec)

        # Order 3: Sneha -> Aura Boutique: Processing (UPI Under Verification with screenshot)
        order3 = Order(
            customer_id=customer2.user_id,
            business_id=biz2.business_id,
            total_amount=Decimal("1149.00"),
            status=Order.STATUS_PROCESSING,
            delivery_address="Row House 14, Lotus Park, Bandra West, Mumbai - 400050",
            notes="Please send Size M for the Kurti.",
            placed_at=now - timedelta(hours=12)
        )
        db.session.add(order3)
        db.session.flush()

        item3_1 = OrderItem(order_id=order3.order_id, product_id=p2_1.product_id, product_name=p2_1.name, quantity=1, unit_price=Decimal("699.00"))
        item3_2 = OrderItem(order_id=order3.order_id, product_id=p2_2.product_id, product_name=p2_2.name, quantity=1, unit_price=Decimal("450.00"))
        db.session.add_all([item3_1, item3_2])

        hist3_1 = OrderStatusHistory(order_id=order3.order_id, status=Order.STATUS_PENDING, changed_at=now - timedelta(hours=12), reason="Order placed by customer.")
        hist3_2 = OrderStatusHistory(order_id=order3.order_id, status=Order.STATUS_CONFIRMED, changed_at=now - timedelta(hours=10), reason="Confirmed by boutique seller.")
        hist3_3 = OrderStatusHistory(order_id=order3.order_id, status=Order.STATUS_PROCESSING, changed_at=now - timedelta(hours=6), reason="Kurti packaging in progress.")
        db.session.add_all([hist3_1, hist3_2, hist3_3])

        pay3_rec = Payment(
            order_id=order3.order_id,
            payment_method=Payment.METHOD_UPI,
            payment_status=Payment.STATUS_UNDER_VERIFICATION,
            screenshot_path=receipt_3,
            updated_at=now - timedelta(hours=11)
        )
        db.session.add(pay3_rec)

        # Order 4: Sneha -> CraftyGifts: Pending (UPI, Pending screenshot)
        order4 = Order(
            customer_id=customer2.user_id,
            business_id=biz1.business_id,
            total_amount=Decimal("499.00"),
            status=Order.STATUS_PENDING,
            delivery_address="Row House 14, Lotus Park, Bandra West, Mumbai - 400050",
            notes="Anniversary gift for a friend.",
            placed_at=now - timedelta(hours=1)
        )
        db.session.add(order4)
        db.session.flush()

        item4_1 = OrderItem(order_id=order4.order_id, product_id=p1_1.product_id, product_name=p1_1.name, quantity=1, unit_price=Decimal("499.00"))
        db.session.add(item4_1)

        hist4_1 = OrderStatusHistory(order_id=order4.order_id, status=Order.STATUS_PENDING, changed_at=now - timedelta(hours=1), reason="Order placed by customer via LocalBizMart.")
        db.session.add(hist4_1)

        pay4_rec = Payment(
            order_id=order4.order_id,
            payment_method=Payment.METHOD_UPI,
            payment_status=Payment.STATUS_PENDING,
            updated_at=now - timedelta(hours=1)
        )
        db.session.add(pay4_rec)

        # Order 5: Sneha -> Creative Corner: Cancelled (by owner with short reason)
        order5 = Order(
            customer_id=customer2.user_id,
            business_id=biz3.business_id,
            total_amount=Decimal("450.00"),
            status=Order.STATUS_CANCELLED,
            delivery_address="Row House 14, Lotus Park, Bandra West, Mumbai - 400050",
            notes="Need by this weekend.",
            cancel_reason="Unable to accept new stitching orders due to heavy festive booking load.",
            placed_at=now - timedelta(days=2)
        )
        db.session.add(order5)
        db.session.flush()

        item5_1 = OrderItem(order_id=order5.order_id, product_id=p3_4.product_id, product_name=p3_4.name, quantity=1, unit_price=Decimal("450.00"))
        db.session.add(item5_1)

        hist5_1 = OrderStatusHistory(order_id=order5.order_id, status=Order.STATUS_PENDING, changed_at=now - timedelta(days=2), reason="Order placed by customer.")
        hist5_2 = OrderStatusHistory(order_id=order5.order_id, status=Order.STATUS_CANCELLED, changed_at=now - timedelta(days=1, hours=20), reason="Cancelled by owner. Reason: Unable to accept new stitching orders due to heavy festive booking load.")
        db.session.add_all([hist5_1, hist5_2])

        pay5_rec = Payment(
            order_id=order5.order_id,
            payment_method=Payment.METHOD_COD,
            payment_status=Payment.STATUS_PENDING,
            updated_at=now - timedelta(days=2)
        )
        db.session.add(pay5_rec)

        db.session.commit()
        print("\nDatabase seeded successfully with diverse local & WhatsApp businesses!")
        print("\n=== Demo Logins Summary ===")
        print("1. Admin: admin@localbizmart.com / Admin@123")
        print("2. Owner (Priya Sen - CraftyGifts, UPI Only): priya@sharmasweets.com / Owner@123")
        print("3. Owner (Anita Desai - Aura Boutique, UPI & COD): anita@craftcorner.com / Owner@123")
        print("4. Owner (Rajesh Kumar - Creative Corner Crafts, COD Only): rajesh@bakersdelight.com / Owner@123")
        print("5. Customer (Rohan Gupta): rohan@customer.com / Customer@123")
        print("6. Customer (Sneha Patel): sneha@customer.com / Customer@123")

if __name__ == '__main__':
    seed_database()
