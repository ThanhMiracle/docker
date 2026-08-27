from typing import Optional
from datetime import datetime, timedelta, timezone
import secrets
from sqlalchemy.orm import Session
from sqlalchemy import or_
from . import models, security
def create_user(
    db: Session,
    email: str,
    password: str,
    is_admin: bool = False
):
    email = email.strip().lower()

    if is_admin:
        verification_token = None
        verification_expires_at = None
    else:
        verification_token = secrets.token_urlsafe(32)
        verification_expires_at = (
            datetime.now(timezone.utc) + timedelta(minutes=30)
        )

    user = models.User(
        email=email,
        hashed_password=security.get_password_hash(password),
        is_admin=is_admin,
        email_verified=is_admin,
        email_verification_token=verification_token,
        email_verification_expires_at=verification_expires_at
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def get_user_by_email(db: Session, email: str):
    email = email.strip().lower()

    return (
        db.query(models.User)
        .filter(models.User.email == email)
        .first()
    )

def verify_user_email(db: Session, token: str):
    user = (
        db.query(models.User)
        .filter(
            models.User.email_verification_token == token,
            models.User.email_verified.is_(False)
        )
        .first()
    )

    if not user:
        return None, "invalid"

    expires_at = user.email_verification_expires_at

    if expires_at is None:
        return None, "invalid"

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < datetime.now(timezone.utc):
        return None, "expired"

    user.email_verified = True
    user.email_verification_token = None
    user.email_verification_expires_at = None

    db.commit()
    db.refresh(user)

    return user, None
def create_product(db: Session, data: dict, owner_id: int):
    p = models.Product(owner_id=owner_id, **data); db.add(p); db.commit(); db.refresh(p); return p
def get_product(db: Session, pid: int):
    return db.query(models.Product).filter(models.Product.id == pid).first()
def update_product(db: Session, pid: int, data: dict, requester_id: int, admin: bool):
    p = get_product(db, pid)
    if not p: return None, "not_found"
    if (p.owner_id != requester_id) and (not admin): return None, "forbidden"
    for k, v in data.items(): setattr(p, k, v)
    db.commit(); db.refresh(p); return p, None
def delete_product(db: Session, pid: int, requester_id: int, admin: bool):
    p = get_product(db, pid)
    if not p: return None, "not_found"
    if (p.owner_id != requester_id) and (not admin): return None, "forbidden"
    db.query(models.CartItem).filter(models.CartItem.product_id == pid).delete()
    db.delete(p); db.commit(); return p, None
def list_products(db: Session, skip: int=0, limit: int=12, q: Optional[str]=None):
    query = db.query(models.Product)
    if q:
        like = f"%{q}%"; query = query.filter(or_(models.Product.name.ilike(like), models.Product.description.ilike(like)))
    total = query.count(); items = query.order_by(models.Product.id.desc()).offset(skip).limit(limit).all()
    return items, total
def list_my_products(db: Session, owner_id: int, skip: int=0, limit: int=12, q: Optional[str]=None):
    query = db.query(models.Product).filter(models.Product.owner_id == owner_id)
    if q:
        like = f"%{q}%"; query = query.filter(or_(models.Product.name.ilike(like), models.Product.description.ilike(like)))
    total = query.count(); items = query.order_by(models.Product.id.desc()).offset(skip).limit(limit).all()
    return items, total

def get_cart_items(db: Session, user_id: int):
    return db.query(models.CartItem).filter(models.CartItem.user_id == user_id).all()

def add_cart_item(db: Session, user_id: int, product_id: int, quantity: int):
    item = db.query(models.CartItem).filter(
        models.CartItem.user_id == user_id, models.CartItem.product_id == product_id
    ).first()
    if item:
        item.quantity += quantity
    else:
        item = models.CartItem(user_id=user_id, product_id=product_id, quantity=quantity)
        db.add(item)
    db.commit(); db.refresh(item)
    return item

def update_cart_item(db: Session, user_id: int, product_id: int, quantity: int):
    item = db.query(models.CartItem).filter(
        models.CartItem.user_id == user_id, models.CartItem.product_id == product_id
    ).first()
    if not item:
        return None
    item.quantity = quantity
    db.commit(); db.refresh(item)
    return item

def remove_cart_item(db: Session, user_id: int, product_id: int):
    item = db.query(models.CartItem).filter(
        models.CartItem.user_id == user_id, models.CartItem.product_id == product_id
    ).first()
    if not item:
        return False
    db.delete(item); db.commit()
    return True

def checkout_cart(db: Session, user_id: int, checkout: dict):
    cart_items = get_cart_items(db, user_id)
    if not cart_items:
        return None
    total = sum(item.product.price * item.quantity for item in cart_items)
    token = secrets.token_urlsafe(32)
    order = models.Order(
        user_id=user_id, total=total, status="pending_confirmation", confirmation_token=token,
        confirmation_expires_at=datetime.now(timezone.utc) + timedelta(minutes=30), **checkout
    )
    db.add(order); db.flush()
    for item in cart_items:
        db.add(models.OrderItem(
            order_id=order.id, product_id=item.product.id, product_name=item.product.name,
            unit_price=item.product.price, quantity=item.quantity
        ))
    db.commit(); db.refresh(order)
    return order

def confirm_order(db: Session, token: str):
    order = db.query(models.Order).filter(
        models.Order.confirmation_token == token, models.Order.status == "pending_confirmation"
    ).first()
    if not order:
        return None, "invalid"
    expires_at = order.confirmation_expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return None, "expired"

    for order_item in order.items:
        cart_item = db.query(models.CartItem).filter(
            models.CartItem.user_id == order.user_id,
            models.CartItem.product_id == order_item.product_id,
        ).first()
        if cart_item:
            if cart_item.quantity <= order_item.quantity:
                db.delete(cart_item)
            else:
                cart_item.quantity -= order_item.quantity
    order.status = "confirmed"
    order.confirmation_token = None
    db.commit(); db.refresh(order)
    return order, None


def cancel_order(db: Session, order_id: int, user_id: int):
    """Cancel an order owned by the current user.

    Pending orders keep their cart unchanged; confirmed orders are not added
    back to the cart automatically, which avoids overwriting later cart edits.
    """
    order = db.query(models.Order).filter(
        models.Order.id == order_id,
        models.Order.user_id == user_id,
    ).first()

    if not order:
        return None, "not_found"
    if order.status not in {"pending_confirmation", "confirmed"}:
        return None, "cannot_cancel"

    order.status = "cancelled"
    order.cancelled_at = datetime.now(timezone.utc)
    order.confirmation_token = None
    order.confirmation_expires_at = None
    db.commit()
    db.refresh(order)
    return order, None


def update_order_delivery(db: Session, order_id: int, user_id: int, data: dict):
    order = db.query(models.Order).filter(
        models.Order.id == order_id,
        models.Order.user_id == user_id,
    ).first()
    if not order:
        return None, "not_found"
    if order.status not in {"pending_confirmation", "confirmed"}:
        return None, "cannot_update"

    order.phone = data["phone"]
    order.delivery_address = data["delivery_address"]
    db.commit()
    db.refresh(order)
    return order, None


def delete_expired_cancelled_orders(db: Session, user_id: int):
    """Permanently remove a user's cancelled orders after five minutes."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
    expired_orders = db.query(models.Order).filter(
        models.Order.user_id == user_id,
        models.Order.status == "cancelled",
        models.Order.cancelled_at <= cutoff,
    ).all()

    if not expired_orders:
        return

    # ORM deletion applies the Order.items relationship cascade, so dependent
    # order items are removed before their parent order.
    for order in expired_orders:
        db.delete(order)
    db.commit()
