from decimal import Decimal
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, current_app
from app.extensions import db
from app.models import Order, OrderItem, OrderStatusHistory, Payment, CartItem, Product, Business
from app.services.whatsapp import WhatsAppService
from app.utils.auth_decorators import login_required, customer_required, get_current_user
from app.utils.helpers import save_upload_file, get_current_time

order_bp = Blueprint('order', __name__, url_prefix='')

@order_bp.route('/checkout', methods=['GET', 'POST'])
@login_required
@customer_required
def checkout():
    user = get_current_user()
    cart_items = CartItem.query.filter_by(customer_id=user.user_id).all()

    if not cart_items:
        flash("Your cart is empty. Please add items to checkout.", "warning")
        return redirect(url_for('browse.businesses'))

    business = cart_items[0].product.business
    payment_settings = business.payment_settings

    # Server-side validation of product availability and prices
    unavailable_items = []
    total_amount = Decimal('0.00')

    for item in cart_items:
        if not item.product.is_purchasable:
            unavailable_items.append(item.product.name)
        else:
            total_amount += item.subtotal

    if unavailable_items:
        names_str = ", ".join(unavailable_items)
        flash(
            f"The following item(s) are currently unavailable: {names_str}. "
            f"Please remove them from your cart to proceed with checkout.",
            "danger"
        )
        return redirect(url_for('cart.view_cart'))

    # Available payment methods for this business
    payment_tracking_enabled = current_app.config.get('PAYMENT_TRACKING_ENABLED', True)
    accepted_methods = []
    if payment_settings:
        if payment_settings.accepts_cod:
            accepted_methods.append('COD')
        if payment_settings.accepts_upi and payment_settings.upi_id:
            accepted_methods.append('UPI')

    if not accepted_methods:
        # Default fallback if unconfigured
        accepted_methods = ['COD']

    if request.method == 'POST':
        delivery_address = request.form.get('delivery_address', '').strip()
        notes = request.form.get('notes', '').strip()
        payment_method = request.form.get('payment_method', 'COD').strip().upper()

        if not delivery_address or len(delivery_address) < 10:
            flash("Please enter a complete delivery address (at least 10 characters).", "danger")
            return render_template(
                'checkout/checkout.html',
                cart_items=cart_items,
                total_amount=total_amount,
                business=business,
                accepted_methods=accepted_methods,
                delivery_address=delivery_address,
                notes=notes,
                selected_payment=payment_method,
                payment_tracking_enabled=payment_tracking_enabled
            )

        if payment_method not in accepted_methods:
            flash("Selected payment method is not accepted by this business.", "danger")
            return render_template(
                'checkout/checkout.html',
                cart_items=cart_items,
                total_amount=total_amount,
                business=business,
                accepted_methods=accepted_methods,
                delivery_address=delivery_address,
                notes=notes,
                payment_tracking_enabled=payment_tracking_enabled
            )

        # Re-check product availability right at the moment of placing order
        for item in cart_items:
            fresh_product = Product.query.get(item.product_id)
            if not fresh_product or not fresh_product.is_purchasable:
                flash(f"'{fresh_product.name if fresh_product else 'An item'}' became unavailable just now. Order was not placed.", "danger")
                return redirect(url_for('cart.view_cart'))

        try:
            # Create Order
            new_order = Order(
                customer_id=user.user_id,
                business_id=business.business_id,
                total_amount=total_amount,
                status=Order.STATUS_PENDING,
                delivery_address=delivery_address,
                notes=notes if notes else None
            )
            db.session.add(new_order)
            db.session.flush()  # Generate order_id

            # Create Order Items (snapshot of product name and unit price)
            for item in cart_items:
                order_item = OrderItem(
                    order_id=new_order.order_id,
                    product_id=item.product_id,
                    product_name=item.product.name,
                    quantity=item.quantity,
                    unit_price=item.product.price
                )
                db.session.add(order_item)

            # Create initial OrderStatusHistory
            history_entry = OrderStatusHistory(
                order_id=new_order.order_id,
                status=Order.STATUS_PENDING,
                reason="Order placed by customer via LocalBizMart."
            )
            db.session.add(history_entry)

            # Create Payment record (payment status separate from order status)
            payment_record = Payment(
                order_id=new_order.order_id,
                payment_method=payment_method,
                payment_status=Payment.STATUS_PENDING
            )
            db.session.add(payment_record)

            # Clear Customer's Cart
            CartItem.query.filter_by(customer_id=user.user_id).delete()

            db.session.commit()
            flash("Your order has been placed successfully!", "success")
            return redirect(url_for('order.order_confirmation', order_id=new_order.order_id))

        except Exception as e:
            db.session.rollback()
            flash("A database error occurred while placing your order. Nothing was charged or saved. Please try again.", "danger")
            return redirect(url_for('cart.view_cart'))

    return render_template(
        'checkout/checkout.html',
        cart_items=cart_items,
        total_amount=total_amount,
        business=business,
        accepted_methods=accepted_methods,
        delivery_address="",
        notes="",
        payment_tracking_enabled=payment_tracking_enabled
    )


@order_bp.route('/order/confirmation/<int:order_id>')
@login_required
@customer_required
def order_confirmation(order_id):
    user = get_current_user()
    order = Order.query.filter_by(order_id=order_id, customer_id=user.user_id).first_or_404()

    # Generate WhatsApp message and direct link for customization & inquiries
    whatsapp_message = WhatsAppService.build_order_customization_inquiry(order)
    whatsapp_link = WhatsAppService.generate_link(order.business.whatsapp_number, whatsapp_message)

    return render_template(
        'order/confirmation.html',
        order=order,
        whatsapp_message=whatsapp_message,
        whatsapp_link=whatsapp_link
    )


@order_bp.route('/orders')
@login_required
@customer_required
def my_orders():
    user = get_current_user()
    orders = Order.query.filter_by(customer_id=user.user_id).order_by(Order.order_id.desc()).all()
    return render_template('order/my_orders.html', orders=orders)


@order_bp.route('/order/<int:order_id>')
@login_required
def order_detail(order_id):
    user = get_current_user()
    order = Order.query.get_or_404(order_id)

    # Security check: Customer can only view their own order; Owner can only view their business's order; Admin can view all
    if user.is_customer and order.customer_id != user.user_id:
        abort(403)
    elif user.is_owner and (not user.business or order.business_id != user.business.business_id):
        abort(403)

    # WhatsApp link for enquiry
    inquiry_msg = WhatsAppService.build_order_inquiry(order)
    whatsapp_link = WhatsAppService.generate_link(order.business.whatsapp_number, inquiry_msg)

    # WhatsApp order confirmation message (for customer convenience)
    whatsapp_message = WhatsAppService.build_message(order)

    return render_template(
        'order/order_detail.html',
        order=order,
        whatsapp_link=whatsapp_link,
        whatsapp_message=whatsapp_message
    )


@order_bp.route('/order/<int:order_id>/cancel', methods=['POST'])
@login_required
@customer_required
def cancel_order(order_id):
    user = get_current_user()
    order = Order.query.filter_by(order_id=order_id, customer_id=user.user_id).first_or_404()

    if not order.can_be_cancelled_by_customer:
        flash("Orders cannot be cancelled once they are in Processing, Shipped, Delivered, or already Cancelled.", "danger")
        return redirect(url_for('order.order_detail', order_id=order.order_id))

    reason = request.form.get('reason', '').strip()
    cancel_text = f"Cancelled by Customer. Reason: {reason}" if reason else "Cancelled by Customer."

    try:
        order.status = Order.STATUS_CANCELLED
        order.cancel_reason = reason if reason else "Cancelled by customer."

        history_entry = OrderStatusHistory(
            order_id=order.order_id,
            status=Order.STATUS_CANCELLED,
            reason=cancel_text
        )
        db.session.add(history_entry)
        db.session.commit()
        flash("Your order has been cancelled.", "info")
    except Exception:
        db.session.rollback()
        flash("Could not cancel order due to a server error. Please try again.", "danger")

    return redirect(url_for('order.order_detail', order_id=order.order_id))


@order_bp.route('/order/<int:order_id>/upload-payment', methods=['POST'])
@login_required
@customer_required
def upload_payment_screenshot(order_id):
    user = get_current_user()
    order = Order.query.filter_by(order_id=order_id, customer_id=user.user_id).first_or_404()

    if not order.payment or order.payment.payment_method != Payment.METHOD_UPI:
        flash("Payment screenshot upload is only applicable for UPI payments.", "warning")
        return redirect(url_for('order.order_detail', order_id=order.order_id))

    if 'screenshot' not in request.files or not request.files['screenshot'].filename:
        flash("Please select a screenshot file to upload.", "danger")
        return redirect(url_for('order.order_detail', order_id=order.order_id))

    file = request.files['screenshot']
    try:
        saved_path = save_upload_file(file, prefix=f"pay_ord{order.order_id}")
        order.payment.screenshot_path = saved_path
        order.payment.payment_status = Payment.STATUS_UNDER_VERIFICATION
        order.payment.updated_at = get_current_time()
        db.session.commit()
        flash("Payment screenshot uploaded successfully! The seller will verify your payment.", "success")
    except ValueError as ve:
        flash(str(ve), "danger")
    except Exception:
        db.session.rollback()
        flash("Failed to upload screenshot. Please ensure it is an image under 2MB.", "danger")

    return redirect(url_for('order.order_detail', order_id=order.order_id))
