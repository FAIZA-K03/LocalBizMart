from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from app.extensions import db
from app.models import Product, ProductImage, Business
from app.utils.auth_decorators import login_required, owner_required, get_current_user
from app.utils.helpers import save_upload_file

product_bp = Blueprint('product', __name__, url_prefix='/owner')

@product_bp.route('/products')
@login_required
@owner_required
def list_products():
    user = get_current_user()
    business = user.business
    if not business:
        flash("Please create your shop profile first before adding products.", "warning")
        return redirect(url_for('business.profile_edit'))

    products = Product.query.filter_by(business_id=business.business_id).order_by(Product.product_id.desc()).all()
    return render_template('product/list.html', business=business, products=products)


@product_bp.route('/product/new', methods=['GET', 'POST'])
@login_required
@owner_required
def create_product():
    user = get_current_user()
    business = user.business
    if not business:
        flash("Please complete your shop profile before adding products.", "warning")
        return redirect(url_for('business.profile_edit'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        price_str = request.form.get('price', '').strip()
        is_available = 'is_available' in request.form

        errors = []
        if not name or len(name) < 2:
            errors.append("Product name is required.")

        try:
            price = Decimal(price_str)
            if price <= Decimal('0.00'):
                errors.append("Price must be greater than zero.")
        except Exception:
            errors.append("Please enter a valid price (e.g., 250.00).")

        # Handle multiple photos (minimum 1, maximum 3)
        raw_files = request.files.getlist('images')
        if not raw_files or not any(f and f.filename for f in raw_files):
            if 'image' in request.files and request.files['image'].filename:
                raw_files = [request.files['image']]

        valid_files = [f for f in raw_files if f and f.filename]
        if len(valid_files) < 1:
            errors.append("Please upload at least 1 product photo (minimum 1, maximum 3 photos required).")
        elif len(valid_files) > 3:
            errors.append("You can upload a maximum of 3 photos for a product.")

        saved_image_paths = []
        if not errors:
            for f in valid_files:
                try:
                    p = save_upload_file(f, prefix="prod")
                    if p:
                        saved_image_paths.append(p)
                except ValueError as ve:
                    errors.append(str(ve))
                except Exception:
                    errors.append("Failed to upload image. Allowed formats: PNG, JPG, JPEG, WEBP under 2MB.")

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template(
                'product/form.html',
                action='Create',
                product=None,
                name=name,
                description=description,
                price=price_str,
                is_available=is_available
            )

        new_product = Product(
            business_id=business.business_id,
            name=name,
            description=description,
            price=price,
            image_path=saved_image_paths[0] if saved_image_paths else None,
            is_available=is_available,
            is_disabled_by_admin=False
        )

        try:
            db.session.add(new_product)
            db.session.flush()

            # Save each photo into ProductImage table
            for idx, path in enumerate(saved_image_paths):
                pi = ProductImage(
                    product_id=new_product.product_id,
                    image_path=path,
                    is_primary=(idx == 0),
                    display_order=idx
                )
                db.session.add(pi)

            db.session.commit()
            flash(f"Product '{new_product.name}' with {len(saved_image_paths)} photo(s) has been added to your catalogue!", "success")
            return redirect(url_for('product.list_products'))
        except Exception:
            db.session.rollback()
            flash("Database error adding product. Please try again.", "danger")

    return render_template('product/form.html', action='Create', product=None, is_available=True)


@product_bp.route('/product/<int:product_id>/edit', methods=['GET', 'POST'])
@login_required
@owner_required
def edit_product(product_id):
    user = get_current_user()
    business = user.business
    if not business:
        abort(403)

    product = Product.query.filter_by(product_id=product_id, business_id=business.business_id).first_or_404()

    # Ensure existing image_path has a row in ProductImage table
    existing_images = ProductImage.query.filter_by(product_id=product.product_id).order_by(ProductImage.display_order.asc()).all()
    if not existing_images and product.image_path:
        default_pi = ProductImage(
            product_id=product.product_id,
            image_path=product.image_path,
            is_primary=True,
            display_order=0
        )
        db.session.add(default_pi)
        db.session.commit()
        existing_images = [default_pi]

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        price_str = request.form.get('price', '').strip()
        is_available = 'is_available' in request.form

        errors = []
        if not name or len(name) < 2:
            errors.append("Product name is required.")

        try:
            price = Decimal(price_str)
            if price <= Decimal('0.00'):
                errors.append("Price must be greater than zero.")
        except Exception:
            errors.append("Please enter a valid price (e.g., 250.00).")

        # Determine photos to remove and new photos to add
        remove_image_ids = set(request.form.getlist('remove_images'))

        raw_files = request.files.getlist('images')
        if not raw_files or not any(f and f.filename for f in raw_files):
            if 'image' in request.files and request.files['image'].filename:
                raw_files = [request.files['image']]

        new_files = [f for f in raw_files if f and f.filename]

        remaining_count = len([img for img in existing_images if str(img.image_id) not in remove_image_ids])
        total_photos = remaining_count + len(new_files)

        if total_photos < 1:
            errors.append("Product must have at least 1 photo (minimum 1, maximum 3).")
        elif total_photos > 3:
            errors.append(f"A product cannot have more than 3 photos in total (currently {remaining_count} retained + {len(new_files)} new = {total_photos}).")

        saved_new_paths = []
        if not errors and new_files:
            for f in new_files:
                try:
                    p = save_upload_file(f, prefix="prod")
                    if p:
                        saved_new_paths.append(p)
                except ValueError as ve:
                    errors.append(str(ve))
                except Exception:
                    errors.append("Failed to upload new image. Allowed formats: PNG, JPG, JPEG, WEBP under 2MB.")

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template(
                'product/form.html',
                action='Edit',
                product=product,
                existing_images=existing_images,
                name=name,
                description=description,
                price=price_str,
                is_available=is_available
            )

        try:
            product.name = name
            product.description = description
            product.price = price
            product.is_available = is_available

            # Delete removed photos
            for img in existing_images:
                if str(img.image_id) in remove_image_ids:
                    db.session.delete(img)

            # Insert new photos
            curr_max_order = max([img.display_order for img in existing_images if str(img.image_id) not in remove_image_ids], default=-1)
            for i, p in enumerate(saved_new_paths):
                new_pi = ProductImage(
                    product_id=product.product_id,
                    image_path=p,
                    is_primary=False,
                    display_order=curr_max_order + 1 + i
                )
                db.session.add(new_pi)

            db.session.flush()

            # Refresh all active images for this product and ensure primary image is set
            updated_images = ProductImage.query.filter_by(product_id=product.product_id).order_by(ProductImage.display_order.asc()).all()
            for idx, img in enumerate(updated_images):
                img.is_primary = (idx == 0)
                img.display_order = idx

            if updated_images:
                product.image_path = updated_images[0].image_path
            else:
                product.image_path = None

            db.session.commit()
            flash(f"Product '{product.name}' updated successfully with {len(updated_images)} photo(s).", "success")
            return redirect(url_for('product.list_products'))
        except Exception:
            db.session.rollback()
            flash("Database error saving changes. Please try again.", "danger")

    return render_template(
        'product/form.html',
        action='Edit',
        product=product,
        existing_images=existing_images,
        name=product.name,
        description=product.description,
        price=product.price,
        is_available=product.is_available
    )


@product_bp.route('/product/<int:product_id>/toggle-availability', methods=['POST'])
@login_required
@owner_required
def toggle_availability(product_id):
    user = get_current_user()
    business = user.business
    if not business:
        abort(403)

    product = Product.query.filter_by(product_id=product_id, business_id=business.business_id).first_or_404()
    product.is_available = not product.is_available

    try:
        db.session.commit()
        status_text = "Available" if product.is_available else "Unavailable"
        flash(f"'{product.name}' is now marked as {status_text}.", "info")
    except Exception:
        db.session.rollback()
        flash("Could not update availability status.", "danger")

    return redirect(url_for('product.list_products'))


@product_bp.route('/product/<int:product_id>/delete', methods=['POST'])
@login_required
@owner_required
def delete_product(product_id):
    user = get_current_user()
    business = user.business
    if not business:
        abort(403)

    product = Product.query.filter_by(product_id=product_id, business_id=business.business_id).first_or_404()
    product_name = product.name

    try:
        # Note: past orders retain product_name and unit_price in order_items; product_id becomes NULL on delete
        db.session.delete(product)
        db.session.commit()
        flash(f"Product '{product_name}' was deleted from your catalogue. Past order records remain intact.", "success")
    except Exception:
        db.session.rollback()
        flash("Failed to delete product.", "danger")

    return redirect(url_for('product.list_products'))
