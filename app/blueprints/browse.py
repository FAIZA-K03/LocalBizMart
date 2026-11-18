from flask import Blueprint, render_template, request, abort, current_app
from app.models import Business, Product, Category
from app.services.whatsapp import WhatsAppService

browse_bp = Blueprint('browse', __name__, url_prefix='')

@browse_bp.route('/')
def index():
    # Only active businesses and active owner accounts
    businesses_query = Business.query.filter_by(status='active').join(Business.owner).filter_by(status='active')
    featured_businesses = businesses_query.limit(6).all()

    # Categories that have at least one business or standard list
    categories = Category.query.all()

    # Recent available products
    recent_products = (
        Product.query
        .filter_by(is_available=True, is_disabled_by_admin=False)
        .join(Product.business)
        .filter_by(status='active')
        .order_by(Product.product_id.desc())
        .limit(8)
        .all()
    )

    return render_template(
        'browse/index.html',
        categories=categories,
        featured_businesses=featured_businesses,
        recent_products=recent_products
    )


@browse_bp.route('/businesses')
def businesses():
    search_query = request.args.get('q', '').strip()
    category_id = request.args.get('category', type=int)

    query = Business.query.filter_by(status='active').join(Business.owner).filter_by(status='active')

    if search_query:
        query = query.filter(Business.name.ilike(f"%{search_query}%"))

    if category_id:
        query = query.filter(Business.category_id == category_id)

    businesses_list = query.order_by(Business.name.asc()).all()
    categories = Category.query.order_by(Category.category_name.asc()).all()

    return render_template(
        'browse/businesses.html',
        businesses=businesses_list,
        categories=categories,
        search_query=search_query,
        selected_category=category_id
    )


@browse_bp.route('/business/<int:business_id>')
def business_detail(business_id):
    business = Business.query.get_or_404(business_id)

    # If business is inactive or owner is inactive, disallow public view unless admin/owner
    if business.status != 'active' or not business.owner.is_active_account:
        from app.utils.auth_decorators import get_current_user
        current_user = get_current_user()
        if not (current_user and (current_user.is_admin or current_user.user_id == business.owner_id)):
            abort(404)

    # Products (hide admin-disabled products from public)
    products = Product.query.filter_by(
        business_id=business.business_id,
        is_disabled_by_admin=False
    ).order_by(Product.is_available.desc(), Product.name.asc()).all()

    # WhatsApp enquiry link for this business
    inquiry_msg = WhatsAppService.build_business_inquiry(business)
    whatsapp_link = WhatsAppService.generate_link(business.whatsapp_number, inquiry_msg)

    return render_template(
        'browse/business_detail.html',
        business=business,
        products=products,
        whatsapp_link=whatsapp_link
    )


@browse_bp.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)

    # Check if disabled by admin
    if product.is_disabled_by_admin:
        from app.utils.auth_decorators import get_current_user
        current_user = get_current_user()
        if not (current_user and (current_user.is_admin or current_user.user_id == product.business.owner_id)):
            abort(404)

    # WhatsApp enquiry link for this product
    inquiry_msg = WhatsAppService.build_product_inquiry(product)
    whatsapp_link = WhatsAppService.generate_link(product.business.whatsapp_number, inquiry_msg)

    return render_template(
        'browse/product_detail.html',
        product=product,
        whatsapp_link=whatsapp_link
    )
