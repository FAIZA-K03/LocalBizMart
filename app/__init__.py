import os
import pymysql
from flask import Flask, render_template
from config import Config
from app.extensions import db, csrf
from app.utils.auth_decorators import get_current_user

def ensure_database_exists(config):
    """
    Connects to MySQL server (using PyMySQL) and ensures the database exists
    before SQLAlchemy initializes connections. Skipped if using SQLite or PostgreSQL.
    """
    uri = getattr(config, 'SQLALCHEMY_DATABASE_URI', '')
    if not uri or not uri.startswith('mysql'):
        return

    try:
        conn = pymysql.connect(
            host=config.DB_HOST,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            port=int(config.DB_PORT),
            connect_timeout=3
        )
        with conn.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{config.DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
            )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Warning] Could not auto-verify MySQL database creation via PyMySQL: {e}")


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure database exists in MySQL
    ensure_database_exists(config_class)

    # Initialize extensions
    db.init_app(app)
    csrf.init_app(app)

    # Ensure uploads directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Context processors for all Jinja2 templates
    @app.context_processor
    def inject_global_data():
        user = get_current_user()
        cart_count = 0
        owner_pending_orders_count = 0

        if user and user.is_customer:
            from app.models import CartItem
            cart_count = CartItem.query.filter_by(customer_id=user.user_id).count()

        if user and user.is_owner and user.business:
            from app.models import Order
            owner_pending_orders_count = Order.query.filter_by(
                business_id=user.business.business_id,
                status=Order.STATUS_PENDING
            ).count()

        return {
            'current_user': user,
            'cart_count': cart_count,
            'owner_pending_orders_count': owner_pending_orders_count,
            'payment_tracking_enabled': app.config.get('PAYMENT_TRACKING_ENABLED', True)
        }

    # Register error handlers
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    # Register blueprints
    from app.blueprints.auth import auth_bp
    from app.blueprints.browse import browse_bp
    from app.blueprints.cart import cart_bp
    from app.blueprints.order import order_bp
    from app.blueprints.business import business_bp
    from app.blueprints.product import product_bp
    from app.blueprints.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(browse_bp)
    app.register_blueprint(cart_bp)
    app.register_blueprint(order_bp)
    app.register_blueprint(business_bp)
    app.register_blueprint(product_bp)
    app.register_blueprint(admin_bp)

    # Auto-create tables on startup and seed if empty
    with app.app_context():
        try:
            db.create_all()
            from app.models import Category
            if Category.query.count() == 0:
                print("[Info] Empty database detected. Auto-seeding initial demo data...")
                from seed import seed_database
                seed_database(app)
        except Exception as e:
            print(f"[Warning] db.create_all() / auto-seed exception: {e}")

    return app
