from datetime import datetime
from decimal import Decimal
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db
from app.utils.helpers import get_current_time

class User(db.Model):
    __tablename__ = 'users'

    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('customer', 'owner', 'admin', name='user_roles'), nullable=False, default='customer')
    status = db.Column(db.Enum('active', 'inactive', name='user_statuses'), nullable=False, default='active')
    created_at = db.Column(db.DateTime, default=get_current_time, nullable=False)

    # Relationships
    business = db.relationship('Business', backref='owner', uselist=False, cascade='all, delete-orphan')
    orders = db.relationship('Order', backref='customer', lazy='dynamic')
    cart_items = db.relationship('CartItem', backref='customer', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_active_account(self):
        return self.status == 'active'

    @property
    def is_customer(self):
        return self.role == 'customer'

    @property
    def is_owner(self):
        return self.role == 'owner'

    @property
    def is_admin(self):
        return self.role == 'admin'

    def __repr__(self):
        return f'<User {self.email} ({self.role})>'


class Category(db.Model):
    __tablename__ = 'categories'

    category_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    category_name = db.Column(db.String(100), unique=True, nullable=False)

    # Relationships
    businesses = db.relationship('Business', backref='category', lazy='dynamic')

    def __repr__(self):
        return f'<Category {self.category_name}>'


class Business(db.Model):
    __tablename__ = 'businesses'

    business_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.category_id', ondelete='RESTRICT'), nullable=False)
    address = db.Column(db.Text, nullable=False)
    whatsapp_number = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='active')  # 'active', 'inactive', 'pending_approval'

    # Relationships
    products = db.relationship('Product', backref='business', lazy='dynamic', cascade='all, delete-orphan')
    orders = db.relationship('Order', backref='business', lazy='dynamic')
    payment_settings = db.relationship('BusinessPaymentSettings', backref='business', uselist=False, cascade='all, delete-orphan')

    @property
    def is_active(self):
        return self.status == 'active'

    def __repr__(self):
        return f'<Business {self.name}>'


class Product(db.Model):
    __tablename__ = 'products'

    product_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.business_id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    image_path = db.Column(db.String(255), nullable=True)
    is_available = db.Column(db.Boolean, default=True, nullable=False)
    is_disabled_by_admin = db.Column(db.Boolean, default=False, nullable=False)

    # Multi-photo relationships
    images = db.relationship('ProductImage', backref='product', lazy='select', cascade='all, delete-orphan', order_by='ProductImage.display_order.asc()')

    @property
    def image_list(self):
        """Returns list of all image paths for this product (1 to 3 images)."""
        if self.images and len(self.images) > 0:
            return [img.image_path for img in self.images]
        if self.image_path:
            return [self.image_path]
        return []

    @property
    def primary_image_path(self):
        imgs = self.image_list
        return imgs[0] if imgs else None

    @property
    def photo_count(self):
        return len(self.image_list)

    @property
    def is_purchasable(self):
        return self.is_available and not self.is_disabled_by_admin

    def __repr__(self):
        return f'<Product {self.name} (Rs. {self.price})>'


class ProductImage(db.Model):
    __tablename__ = 'product_images'

    image_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id', ondelete='CASCADE'), nullable=False)
    image_path = db.Column(db.String(255), nullable=False)
    is_primary = db.Column(db.Boolean, default=False, nullable=False)
    display_order = db.Column(db.Integer, default=0, nullable=False)

    def __repr__(self):
        return f'<ProductImage #{self.image_id} prod={self.product_id} path={self.image_path}>'


class CartItem(db.Model):
    __tablename__ = 'cart_items'
    __table_args__ = (
        db.UniqueConstraint('customer_id', 'product_id', name='unique_customer_product'),
    )

    cart_item_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id', ondelete='CASCADE'), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)

    product = db.relationship('Product')

    @property
    def subtotal(self):
        if self.product and self.product.price:
            return round(Decimal(self.product.price) * Decimal(self.quantity), 2)
        return Decimal('0.00')

    def __repr__(self):
        return f'<CartItem user={self.customer_id} product={self.product_id} qty={self.quantity}>'


class Order(db.Model):
    __tablename__ = 'orders'

    STATUS_PENDING = 'Pending'
    STATUS_CONFIRMED = 'Confirmed'
    STATUS_PROCESSING = 'Processing'
    STATUS_SHIPPED = 'Shipped'
    STATUS_DELIVERED = 'Delivered'
    STATUS_CANCELLED = 'Cancelled'

    ALL_STATUSES = [
        STATUS_PENDING,
        STATUS_CONFIRMED,
        STATUS_PROCESSING,
        STATUS_SHIPPED,
        STATUS_DELIVERED,
        STATUS_CANCELLED
    ]

    order_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='RESTRICT'), nullable=False)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.business_id', ondelete='RESTRICT'), nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(30), default=STATUS_PENDING, nullable=False)
    delivery_address = db.Column(db.Text, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    cancel_reason = db.Column(db.Text, nullable=True)
    placed_at = db.Column(db.DateTime, default=get_current_time, nullable=False)
    updated_at = db.Column(db.DateTime, default=get_current_time, onupdate=get_current_time, nullable=False)

    # Relationships
    items = db.relationship('OrderItem', backref='order', lazy='select', cascade='all, delete-orphan')
    status_history = db.relationship('OrderStatusHistory', backref='order', lazy='select', cascade='all, delete-orphan', order_by='OrderStatusHistory.changed_at.asc()')
    payment = db.relationship('Payment', backref='order', uselist=False, cascade='all, delete-orphan')

    @property
    def can_be_cancelled_by_customer(self):
        return self.status in [self.STATUS_PENDING, self.STATUS_CONFIRMED]

    @property
    def is_terminal_status(self):
        return self.status in [self.STATUS_DELIVERED, self.STATUS_CANCELLED]

    def valid_next_statuses_for_owner(self):
        transitions = {
            self.STATUS_PENDING: [self.STATUS_CONFIRMED, self.STATUS_PROCESSING, self.STATUS_CANCELLED],
            self.STATUS_CONFIRMED: [self.STATUS_PROCESSING, self.STATUS_CANCELLED],
            self.STATUS_PROCESSING: [self.STATUS_SHIPPED, self.STATUS_CANCELLED],
            self.STATUS_SHIPPED: [self.STATUS_DELIVERED],
            self.STATUS_DELIVERED: [],
            self.STATUS_CANCELLED: []
        }
        return transitions.get(self.status, [])

    def __repr__(self):
        return f'<Order #{self.order_id} [{self.status}] Rs. {self.total_amount}>'


class OrderItem(db.Model):
    __tablename__ = 'order_items'

    order_item_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.order_id', ondelete='CASCADE'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id', ondelete='SET NULL'), nullable=True)
    product_name = db.Column(db.String(150), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)

    product = db.relationship('Product')

    @property
    def subtotal(self):
        return round(Decimal(self.unit_price) * Decimal(self.quantity), 2)

    def __repr__(self):
        return f'<OrderItem {self.product_name} x {self.quantity}>'


class OrderStatusHistory(db.Model):
    __tablename__ = 'order_status_history'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.order_id', ondelete='CASCADE'), nullable=False)
    status = db.Column(db.String(30), nullable=False)
    changed_at = db.Column(db.DateTime, default=get_current_time, nullable=False)
    reason = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<OrderStatusHistory order={self.order_id} status={self.status}>'


class BusinessPaymentSettings(db.Model):
    __tablename__ = 'business_payment_settings'

    business_id = db.Column(db.Integer, db.ForeignKey('businesses.business_id', ondelete='CASCADE'), primary_key=True)
    accepts_upi = db.Column(db.Boolean, default=False, nullable=False)
    upi_id = db.Column(db.String(100), nullable=True)
    accepts_cod = db.Column(db.Boolean, default=True, nullable=False)

    def has_valid_settings(self):
        if not self.accepts_upi and not self.accepts_cod:
            return False
        if self.accepts_upi and not self.upi_id:
            return False
        return True

    def __repr__(self):
        return f'<BusinessPaymentSettings business={self.business_id} upi={self.accepts_upi} cod={self.accepts_cod}>'


class Payment(db.Model):
    __tablename__ = 'payments'

    METHOD_UPI = 'UPI'
    METHOD_COD = 'COD'

    STATUS_PENDING = 'Pending'
    STATUS_UNDER_VERIFICATION = 'Under Verification'
    STATUS_PAID = 'Paid'
    STATUS_VERIFICATION_FAILED = 'Verification Failed'

    payment_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.order_id', ondelete='CASCADE'), unique=True, nullable=False)
    payment_method = db.Column(db.String(20), nullable=False)  # 'UPI', 'COD'
    payment_status = db.Column(db.String(30), default=STATUS_PENDING, nullable=False)
    screenshot_path = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(db.DateTime, default=get_current_time, onupdate=get_current_time, nullable=False)

    def __repr__(self):
        return f'<Payment order={self.order_id} method={self.payment_method} status={self.payment_status}>'
