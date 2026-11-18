from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from app.extensions import db
from app.models import CartItem, Product, Business
from app.utils.auth_decorators import login_required, customer_required, get_current_user

cart_bp = Blueprint('cart', __name__, url_prefix='/cart')

@cart_bp.route('')
@cart_bp.route('/')
@login_required
@customer_required
def view_cart():
    user = get_current_user()
    items = CartItem.query.filter_by(customer_id=user.user_id).all()

    total_amount = Decimal('0.00')
    has_unavailable_items = False
    business = None

    for item in items:
        if not item.product.is_purchasable:
            has_unavailable_items = True
        else:
            total_amount += item.subtotal
        if not business and item.product:
            business = item.product.business

    return render_template(
        'cart/cart.html',
        items=items,
        total_amount=total_amount,
        has_unavailable_items=has_unavailable_items,
        business=business
    )


@cart_bp.route('/add/<int:product_id>', methods=['POST'])
@login_required
@customer_required
def add_to_cart(product_id):
    user = get_current_user()
    product = Product.query.get_or_404(product_id)

    # Validate availability
    if not product.is_purchasable:
        flash(f"Sorry, '{product.name}' is currently unavailable and cannot be added to your cart.", "danger")
        return redirect(request.referrer or url_for('browse.product_detail', product_id=product_id))

    quantity = request.form.get('quantity', 1, type=int)
    if quantity < 1:
        quantity = 1

    # Check for multi-business conflict
    existing_items = CartItem.query.filter_by(customer_id=user.user_id).all()
    if existing_items:
        current_cart_business = existing_items[0].product.business
        if current_cart_business.business_id != product.business_id:
            flash(
                f"Your cart already has items from '{current_cart_business.name}'. "
                f"LocalBizMart orders are fulfilled by individual shops. "
                f"Please complete or clear your current cart to order from '{product.business.name}'.",
                "warning"
            )
            return redirect(url_for('cart.view_cart'))

    # Check if product is already in cart
    existing_cart_item = CartItem.query.filter_by(
        customer_id=user.user_id,
        product_id=product.product_id
    ).first()

    if existing_cart_item:
        existing_cart_item.quantity += quantity
    else:
        new_item = CartItem(
            customer_id=user.user_id,
            product_id=product.product_id,
            quantity=quantity
        )
        db.session.add(new_item)

    try:
        db.session.commit()
        flash(f"Added {quantity} x '{product.name}' to your cart.", "success")
    except Exception as e:
        db.session.rollback()
        flash("Failed to add item to cart. Please try again.", "danger")

    return redirect(url_for('cart.view_cart'))


@cart_bp.route('/clear-and-add/<int:product_id>', methods=['POST'])
@login_required
@customer_required
def clear_and_add(product_id):
    """Clears the existing cart from another business and adds the new product."""
    user = get_current_user()
    product = Product.query.get_or_404(product_id)

    if not product.is_purchasable:
        flash(f"'{product.name}' is currently unavailable.", "danger")
        return redirect(url_for('browse.product_detail', product_id=product_id))

    quantity = request.form.get('quantity', 1, type=int)
    if quantity < 1:
        quantity = 1

    try:
        CartItem.query.filter_by(customer_id=user.user_id).delete()
        new_item = CartItem(
            customer_id=user.user_id,
            product_id=product.product_id,
            quantity=quantity
        )
        db.session.add(new_item)
        db.session.commit()
        flash(f"Cart cleared. Added '{product.name}' to your new cart.", "success")
    except Exception:
        db.session.rollback()
        flash("Could not update cart. Please try again.", "danger")

    return redirect(url_for('cart.view_cart'))


@cart_bp.route('/update/<int:cart_item_id>', methods=['POST'])
@login_required
@customer_required
def update_quantity(cart_item_id):
    user = get_current_user()
    cart_item = CartItem.query.filter_by(cart_item_id=cart_item_id, customer_id=user.user_id).first_or_404()

    quantity = request.form.get('quantity', type=int)
    if quantity is None or quantity < 1:
        flash("Quantity must be at least 1.", "warning")
        return redirect(url_for('cart.view_cart'))

    cart_item.quantity = quantity
    try:
        db.session.commit()
        flash("Cart quantity updated.", "success")
    except Exception:
        db.session.rollback()
        flash("Could not update quantity. Please try again.", "danger")

    return redirect(url_for('cart.view_cart'))


@cart_bp.route('/remove/<int:cart_item_id>', methods=['POST'])
@login_required
@customer_required
def remove_item(cart_item_id):
    user = get_current_user()
    cart_item = CartItem.query.filter_by(cart_item_id=cart_item_id, customer_id=user.user_id).first_or_404()

    product_name = cart_item.product.name if cart_item.product else "Item"
    try:
        db.session.delete(cart_item)
        db.session.commit()
        flash(f"Removed '{product_name}' from your cart.", "info")
    except Exception:
        db.session.rollback()
        flash("Could not remove item. Please try again.", "danger")

    return redirect(url_for('cart.view_cart'))


@cart_bp.route('/clear', methods=['POST'])
@login_required
@customer_required
def clear_cart():
    user = get_current_user()
    try:
        CartItem.query.filter_by(customer_id=user.user_id).delete()
        db.session.commit()
        flash("Your cart has been cleared.", "info")
    except Exception:
        db.session.rollback()
        flash("Could not clear cart. Please try again.", "danger")

    return redirect(url_for('cart.view_cart'))
