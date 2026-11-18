from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, current_app
from app.extensions import db
from app.models import User, Business, Product, Order, Category, Payment
from app.utils.auth_decorators import login_required, admin_required, get_current_user

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    users_count = User.query.count()
    businesses_count = Business.query.count()
    products_count = Product.query.count()
    orders_count = Order.query.count()

    recent_users = User.query.order_by(User.user_id.desc()).limit(5).all()
    recent_orders = Order.query.order_by(Order.order_id.desc()).limit(5).all()
    pending_approval_count = Business.query.filter_by(status='pending_approval').count()

    return render_template(
        'admin/dashboard.html',
        users_count=users_count,
        businesses_count=businesses_count,
        products_count=products_count,
        orders_count=orders_count,
        recent_users=recent_users,
        recent_orders=recent_orders,
        pending_approval_count=pending_approval_count
    )


@admin_bp.route('/users')
@login_required
@admin_required
def users_list():
    role_filter = request.args.get('role', '').strip()
    status_filter = request.args.get('status', '').strip()

    query = User.query

    if role_filter:
        query = query.filter_by(role=role_filter)
    if status_filter:
        query = query.filter_by(status=status_filter)

    users = query.order_by(User.user_id.desc()).all()
    return render_template('admin/users.html', users=users, role_filter=role_filter, status_filter=status_filter)


@admin_bp.route('/user/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_user_status(user_id):
    current_admin = get_current_user()
    if current_admin.user_id == user_id:
        flash("You cannot deactivate your own administrative account.", "danger")
        return redirect(url_for('admin.users_list'))

    user = User.query.get_or_404(user_id)
    user.status = 'inactive' if user.status == 'active' else 'active'

    try:
        db.session.commit()
        status_label = "activated" if user.status == 'active' else "deactivated"
        flash(f"User account '{user.email}' has been {status_label}.", "info")
    except Exception:
        db.session.rollback()
        flash("Failed to update user status.", "danger")

    return redirect(url_for('admin.users_list'))


@admin_bp.route('/user/<int:user_id>/soft-remove', methods=['POST'])
@login_required
@admin_required
def soft_remove_user(user_id):
    current_admin = get_current_user()
    if current_admin.user_id == user_id:
        flash("You cannot remove your own administrative account.", "danger")
        return redirect(url_for('admin.users_list'))

    user = User.query.get_or_404(user_id)
    # Soft removal: mark as inactive and update status so orders remain connected
    user.status = 'inactive'
    if user.business:
        user.business.status = 'inactive'

    try:
        db.session.commit()
        flash(f"User '{user.name}' ({user.email}) has been deactivated and safely soft-removed without breaking historical orders.", "warning")
    except Exception:
        db.session.rollback()
        flash("Failed to soft-remove user.", "danger")

    return redirect(url_for('admin.users_list'))


@admin_bp.route('/businesses')
@login_required
@admin_required
def businesses_list():
    status_filter = request.args.get('status', '').strip()
    query = Business.query

    if status_filter:
        query = query.filter_by(status=status_filter)

    businesses = query.order_by(Business.business_id.desc()).all()
    return render_template('admin/businesses.html', businesses=businesses, status_filter=status_filter)


@admin_bp.route('/business/<int:business_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_business_status(business_id):
    business = Business.query.get_or_404(business_id)

    if business.status == 'active':
        business.status = 'inactive'
    else:
        business.status = 'active'

    try:
        db.session.commit()
        flash(f"Business '{business.name}' visibility updated to '{business.status}'.", "info")
    except Exception:
        db.session.rollback()
        flash("Failed to update business status.", "danger")

    return redirect(url_for('admin.businesses_list'))


@admin_bp.route('/business/<int:business_id>/remove', methods=['POST'])
@login_required
@admin_required
def remove_business(business_id):
    business = Business.query.get_or_404(business_id)
    business_name = business.name

    # Check if business has existing orders; if yes, deactivate rather than delete to preserve order records
    if business.orders.count() > 0:
        business.status = 'inactive'
        try:
            db.session.commit()
            flash(f"Business '{business_name}' has past orders, so its visibility was deactivated (soft-removed) to preserve order history.", "warning")
        except Exception:
            db.session.rollback()
            flash("Failed to deactivate business.", "danger")
    else:
        try:
            db.session.delete(business)
            db.session.commit()
            flash(f"Business '{business_name}' removed completely.", "success")
        except Exception:
            db.session.rollback()
            flash("Failed to remove business.", "danger")

    return redirect(url_for('admin.businesses_list'))


@admin_bp.route('/products')
@login_required
@admin_required
def products_list():
    products = Product.query.order_by(Product.product_id.desc()).all()
    return render_template('admin/products.html', products=products)


@admin_bp.route('/product/<int:product_id>/toggle-disable', methods=['POST'])
@login_required
@admin_required
def toggle_product_disable(product_id):
    product = Product.query.get_or_404(product_id)
    product.is_disabled_by_admin = not product.is_disabled_by_admin

    try:
        db.session.commit()
        action_str = "moderated/disabled" if product.is_disabled_by_admin else "approved/re-enabled"
        flash(f"Product '{product.name}' has been {action_str} by administrator.", "info")
    except Exception:
        db.session.rollback()
        flash("Failed to update product moderation state.", "danger")

    return redirect(url_for('admin.products_list'))


@admin_bp.route('/product/<int:product_id>/delete', methods=['POST'])
@login_required
@admin_required
def remove_product(product_id):
    product = Product.query.get_or_404(product_id)
    product_name = product.name

    try:
        db.session.delete(product)
        db.session.commit()
        flash(f"Product '{product_name}' was removed by admin. Past orders retain historical items.", "success")
    except Exception:
        db.session.rollback()
        flash("Failed to remove product.", "danger")

    return redirect(url_for('admin.products_list'))


@admin_bp.route('/orders')
@login_required
@admin_required
def orders_list():
    # Read-only order overview across platform
    orders = Order.query.order_by(Order.order_id.desc()).all()
    return render_template('admin/orders.html', orders=orders)


@admin_bp.route('/categories', methods=['GET', 'POST'])
@login_required
@admin_required
def categories():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add':
            category_name = request.form.get('category_name', '').strip()
            if not category_name or len(category_name) < 2:
                flash("Category name must be at least 2 characters.", "danger")
            elif Category.query.filter_by(category_name=category_name).first():
                flash("Category with this name already exists.", "warning")
            else:
                new_cat = Category(category_name=category_name)
                try:
                    db.session.add(new_cat)
                    db.session.commit()
                    flash(f"Category '{category_name}' created successfully.", "success")
                except Exception:
                    db.session.rollback()
                    flash("Failed to create category.", "danger")

        elif action == 'edit':
            category_id = request.form.get('category_id', type=int)
            category_name = request.form.get('category_name', '').strip()
            cat = Category.query.get_or_404(category_id)

            if not category_name or len(category_name) < 2:
                flash("Category name must be at least 2 characters.", "danger")
            else:
                cat.category_name = category_name
                try:
                    db.session.commit()
                    flash(f"Category updated to '{category_name}'.", "success")
                except Exception:
                    db.session.rollback()
                    flash("Failed to update category name.", "danger")

        elif action == 'delete':
            category_id = request.form.get('category_id', type=int)
            cat = Category.query.get_or_404(category_id)

            if cat.businesses.count() > 0:
                flash(f"Cannot delete category '{cat.category_name}' because it has {cat.businesses.count()} registered business(es).", "danger")
            else:
                try:
                    db.session.delete(cat)
                    db.session.commit()
                    flash(f"Category '{cat.category_name}' deleted.", "info")
                except Exception:
                    db.session.rollback()
                    flash("Failed to delete category.", "danger")

        return redirect(url_for('admin.categories'))

    all_categories = Category.query.order_by(Category.category_name.asc()).all()
    return render_template('admin/categories.html', categories=all_categories)
