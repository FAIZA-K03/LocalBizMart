from datetime import datetime
from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, current_app
from app.extensions import db
from app.models import Business, BusinessPaymentSettings, Category, Order, OrderStatusHistory, Payment, Product
from app.utils.auth_decorators import login_required, owner_required, get_current_user
from app.utils.helpers import validate_phone, validate_upi_id, get_current_time
from app.services.whatsapp import WhatsAppService

business_bp = Blueprint('business', __name__, url_prefix='/owner')

@business_bp.route('/dashboard')
@login_required
@owner_required
def dashboard():
    user = get_current_user()
    business = user.business

    if not business:
        flash("Please complete your business profile setup first.", "info")
        return redirect(url_for('business.profile_edit'))

    # Metrics
    total_products = Product.query.filter_by(business_id=business.business_id).count()
    active_products = Product.query.filter_by(business_id=business.business_id, is_available=True, is_disabled_by_admin=False).count()

    total_orders = Order.query.filter_by(business_id=business.business_id).count()
    pending_orders = Order.query.filter_by(business_id=business.business_id, status=Order.STATUS_PENDING).count()

    # Calculate total revenue from delivered orders
    delivered_orders = Order.query.filter_by(business_id=business.business_id, status=Order.STATUS_DELIVERED).all()
    total_revenue = sum(order.total_amount for order in delivered_orders) if delivered_orders else Decimal('0.00')

    # Pending payment verifications
    pending_payments = (
        Payment.query
        .join(Payment.order)
        .filter(Order.business_id == business.business_id, Payment.payment_status == Payment.STATUS_UNDER_VERIFICATION)
        .count()
    )

    recent_orders = (
        Order.query
        .filter_by(business_id=business.business_id)
        .order_by(Order.order_id.desc())
        .limit(5)
        .all()
    )

    return render_template(
        'business/dashboard.html',
        business=business,
        total_products=total_products,
        active_products=active_products,
        total_orders=total_orders,
        pending_orders=pending_orders,
        total_revenue=total_revenue,
        pending_payments=pending_payments,
        recent_orders=recent_orders
    )


@business_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@owner_required
def profile_edit():
    user = get_current_user()
    business = user.business
    categories = Category.query.order_by(Category.category_name.asc()).all()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        category_id = request.form.get('category_id', type=int)
        address = request.form.get('address', '').strip()
        whatsapp_number = request.form.get('whatsapp_number', '').strip()

        errors = []
        if not name or len(name) < 3:
            errors.append("Business name must be at least 3 characters long.")
        if not category_id or not Category.query.get(category_id):
            errors.append("Please select a valid business category.")
        if not address or len(address) < 5:
            errors.append("Please provide a valid shop/workshop address.")
        if not validate_phone(whatsapp_number):
            errors.append("Please provide a valid 10-14 digit WhatsApp contact number.")

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template(
                'business/profile_edit.html',
                business=business,
                categories=categories,
                form_data=request.form
            )

        try:
            if not business:
                # Require admin approval config check
                req_approval = current_app.config.get('REQUIRE_ADMIN_APPROVAL', False)
                initial_status = 'pending_approval' if req_approval else 'active'

                business = Business(
                    owner_id=user.user_id,
                    name=name,
                    description=description,
                    category_id=category_id,
                    address=address,
                    whatsapp_number=whatsapp_number,
                    status=initial_status
                )
                db.session.add(business)
                db.session.flush()

                # Create default payment settings for new business
                default_settings = BusinessPaymentSettings(
                    business_id=business.business_id,
                    accepts_upi=False,
                    upi_id=None,
                    accepts_cod=True
                )
                db.session.add(default_settings)
                db.session.commit()

                flash("Business profile created successfully! Now configure your payment options.", "success")
                return redirect(url_for('business.payment_settings'))
            else:
                business.name = name
                business.description = description
                business.category_id = category_id
                business.address = address
                business.whatsapp_number = whatsapp_number
                db.session.commit()
                flash("Business profile updated successfully.", "success")
                return redirect(url_for('business.dashboard'))

        except Exception as e:
            db.session.rollback()
            flash("Failed to save business profile. Please try again.", "danger")

    return render_template('business/profile_edit.html', business=business, categories=categories)


@business_bp.route('/payment-settings', methods=['GET', 'POST'])
@login_required
@owner_required
def payment_settings():
    user = get_current_user()
    business = user.business
    if not business:
        flash("Please create your business profile first.", "warning")
        return redirect(url_for('business.profile_edit'))

    settings = business.payment_settings
    if not settings:
        settings = BusinessPaymentSettings(business_id=business.business_id, accepts_upi=False, accepts_cod=True)
        db.session.add(settings)
        db.session.commit()

    if request.method == 'POST':
        accepts_upi = 'accepts_upi' in request.form
        upi_id = request.form.get('upi_id', '').strip()
        accepts_cod = 'accepts_cod' in request.form

        errors = []
        if not accepts_upi and not accepts_cod:
            errors.append("You must enable at least one payment method (UPI or Cash on Delivery).")

        if accepts_upi:
            if not upi_id:
                errors.append("Please enter your UPI ID since UPI is enabled.")
            elif not validate_upi_id(upi_id):
                errors.append("Invalid UPI ID format. Standard format is username@bank (e.g. 9876543210@paytm, store@okhdfcbank).")

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template('business/payment_settings.html', business=business, settings=settings)

        settings.accepts_upi = accepts_upi
        settings.upi_id = upi_id if accepts_upi else None
        settings.accepts_cod = accepts_cod

        try:
            db.session.commit()
            flash("Payment settings updated successfully.", "success")
            return redirect(url_for('business.dashboard'))
        except Exception:
            db.session.rollback()
            flash("Failed to update payment settings. Please try again.", "danger")

    return render_template('business/payment_settings.html', business=business, settings=settings)


@business_bp.route('/orders')
@login_required
@owner_required
def incoming_orders():
    user = get_current_user()
    business = user.business
    if not business:
        flash("Please set up your business profile first.", "warning")
        return redirect(url_for('business.profile_edit'))

    status_filter = request.args.get('status', '').strip()
    query = Order.query.filter_by(business_id=business.business_id)

    if status_filter and status_filter in Order.ALL_STATUSES:
        query = query.filter_by(status=status_filter)

    orders = query.order_by(Order.order_id.desc()).all()

    return render_template(
        'business/incoming_orders.html',
        business=business,
        orders=orders,
        current_status_filter=status_filter,
        all_statuses=Order.ALL_STATUSES
    )


@business_bp.route('/order/<int:order_id>')
@login_required
@owner_required
def order_detail(order_id):
    user = get_current_user()
    business = user.business
    if not business:
        abort(403)

    order = Order.query.filter_by(order_id=order_id, business_id=business.business_id).first_or_404()

    # WhatsApp link for owner to message customer
    wa_msg = f"Hello {order.customer.name}! This is {business.name} regarding your order #LBM-{order.order_id}."
    customer_wa_link = WhatsAppService.generate_link(order.customer.phone, wa_msg)

    valid_next_statuses = order.valid_next_statuses_for_owner()

    return render_template(
        'business/order_detail.html',
        business=business,
        order=order,
        valid_next_statuses=valid_next_statuses,
        customer_wa_link=customer_wa_link
    )


@business_bp.route('/order/<int:order_id>/update-status', methods=['POST'])
@login_required
@owner_required
def update_order_status(order_id):
    user = get_current_user()
    business = user.business
    if not business:
        abort(403)

    order = Order.query.filter_by(order_id=order_id, business_id=business.business_id).first_or_404()
    new_status = request.form.get('new_status', '').strip()
    cancel_reason = request.form.get('cancel_reason', '').strip()

    valid_transitions = order.valid_next_statuses_for_owner()

    if new_status not in valid_transitions:
        flash(f"Invalid status transition from '{order.status}' to '{new_status}'.", "danger")
        return redirect(url_for('business.order_detail', order_id=order.order_id))

    if new_status == Order.STATUS_CANCELLED and not cancel_reason:
        flash("A cancellation reason is required when cancelling an order.", "danger")
        return redirect(url_for('business.order_detail', order_id=order.order_id))

    # Payment rule for UPI: Must verify payment (marked Paid) before Confirming or Processing
    if new_status in [Order.STATUS_CONFIRMED, Order.STATUS_PROCESSING]:
        if order.payment and order.payment.payment_method == Payment.METHOD_UPI:
            if order.payment.payment_status != Payment.STATUS_PAID:
                flash(
                    "For UPI orders, payment must be verified and marked as 'Paid' before confirming or processing the order. "
                    "Please verify the payment receipt first.",
                    "danger"
                )
                return redirect(url_for('business.order_detail', order_id=order.order_id))

    try:
        old_status = order.status
        now = get_current_time()

        # Handle the "Confirm & Start Processing" shortcut directly from Pending -> Processing
        if old_status == Order.STATUS_PENDING and new_status == Order.STATUS_PROCESSING:
            order.status = Order.STATUS_PROCESSING
            order.updated_at = now

            # Record Confirmed step in history
            hist_confirm = OrderStatusHistory(
                order_id=order.order_id,
                status=Order.STATUS_CONFIRMED,
                changed_at=now,
                reason="Order confirmed by seller."
            )
            # Record Processing step in history
            hist_process = OrderStatusHistory(
                order_id=order.order_id,
                status=Order.STATUS_PROCESSING,
                changed_at=now,
                reason="Order confirmed and packaging/processing started immediately by seller."
            )
            db.session.add_all([hist_confirm, hist_process])
            db.session.commit()
            flash(f"Order #{order.order_id} confirmed and moved to Processing!", "success")
            return redirect(url_for('business.order_detail', order_id=order.order_id))

        # Standard status transition
        order.status = new_status
        order.updated_at = now

        reason_text = f"Status updated from {old_status} to {new_status} by seller."
        if new_status == Order.STATUS_CANCELLED:
            order.cancel_reason = cancel_reason
            reason_text = f"Cancelled by seller. Reason: {cancel_reason}"

        # Automatic payment status update for COD upon delivery
        if new_status == Order.STATUS_DELIVERED and order.payment and order.payment.payment_method == Payment.METHOD_COD:
            order.payment.payment_status = Payment.STATUS_PAID
            order.payment.updated_at = now
            reason_text = f"Delivered to customer. Cash on Delivery (₹{order.total_amount}) collected and marked as Paid."

        history_entry = OrderStatusHistory(
            order_id=order.order_id,
            status=new_status,
            changed_at=now,
            reason=reason_text
        )
        db.session.add(history_entry)
        db.session.commit()

        if new_status == Order.STATUS_DELIVERED and order.payment and order.payment.payment_method == Payment.METHOD_COD:
            flash(f"Order #{order.order_id} marked as Delivered! Cash on Delivery payment has been marked as Paid.", "success")
        else:
            flash(f"Order #{order.order_id} status updated to '{new_status}'.", "success")

    except Exception:
        db.session.rollback()
        flash("Could not update order status due to a database error.", "danger")

    return redirect(url_for('business.order_detail', order_id=order.order_id))


@business_bp.route('/order/<int:order_id>/verify-payment', methods=['POST'])
@login_required
@owner_required
def verify_payment(order_id):
    user = get_current_user()
    business = user.business
    if not business:
        abort(403)

    order = Order.query.filter_by(order_id=order_id, business_id=business.business_id).first_or_404()
    new_payment_status = request.form.get('payment_status', '').strip()

    allowed_statuses = [Payment.STATUS_PAID, Payment.STATUS_VERIFICATION_FAILED]

    if new_payment_status not in allowed_statuses:
        flash("Invalid payment status update.", "danger")
        return redirect(url_for('business.order_detail', order_id=order.order_id))

    # Payment rule for COD: Cannot mark as Paid before the order is Delivered
    if order.payment.payment_method == Payment.METHOD_COD:
        if new_payment_status == Payment.STATUS_PAID and order.status != Order.STATUS_DELIVERED:
            flash(
                "Cash on Delivery payment can only be marked as 'Paid' once the order has been Delivered to the customer. "
                "Cash is collected upon doorstep delivery.",
                "danger"
            )
            return redirect(url_for('business.order_detail', order_id=order.order_id))

    try:
        order.payment.payment_status = new_payment_status
        order.payment.updated_at = get_current_time()
        db.session.commit()
        flash(f"Payment status for Order #{order.order_id} updated to '{new_payment_status}'.", "success")
    except Exception:
        db.session.rollback()
        flash("Failed to update payment status.", "danger")

    return redirect(url_for('business.order_detail', order_id=order.order_id))
