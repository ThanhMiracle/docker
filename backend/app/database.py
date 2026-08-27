import json
import os
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()
def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def migrate_order_delivery_fields():
    """Add checkout fields for databases created before delivery details existed."""
    inspector = inspect(engine)
    if "orders" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("orders")}
    required_columns = {
        "customer_name": "VARCHAR(120) NOT NULL DEFAULT ''",
        "phone": "VARCHAR(40) NOT NULL DEFAULT ''",
        "delivery_address": "TEXT NOT NULL DEFAULT ''",
    }
    with engine.begin() as connection:
        for name, definition in required_columns.items():
            if name not in existing_columns:
                connection.execute(text(f"ALTER TABLE orders ADD COLUMN {name} {definition}"))

def configure_single_admin(email: str | None):
    """Make the configured account the only admin and automatically verify it."""

    if not email:
        return

    db = SessionLocal()

    try:
        from .models import User

        normalized_email = email.strip().lower()

        admin = (
            db.query(User)
            .filter(User.email == normalized_email)
            .first()
        )

        if not admin:
            return

        # Remove admin role from all other users
        db.query(User).filter(
            User.id != admin.id,
            User.is_admin.is_(True)
        ).update(
            {"is_admin": False},
            synchronize_session=False
        )

        # ADMIN_EMAIL is automatically verified
        admin.is_admin = True
        admin.email_verified = True
        admin.email_verification_token = None
        admin.email_verification_expires_at = None

        db.commit()

    finally:
        db.close()

def migrate_order_confirmation_fields():
    inspector = inspect(engine)
    if "orders" not in inspector.get_table_names():
        return
    existing_columns = {column["name"] for column in inspector.get_columns("orders")}
    required_columns = {
        "status": "VARCHAR(30) NOT NULL DEFAULT 'confirmed'",
        "confirmation_token": "VARCHAR(255)",
        "confirmation_expires_at": "TIMESTAMP WITH TIME ZONE",
    }
    with engine.begin() as connection:
        for name, definition in required_columns.items():
            if name not in existing_columns:
                connection.execute(text(f"ALTER TABLE orders ADD COLUMN {name} {definition}"))

def migrate_order_cancellation_fields():
    """Add the cancellation timestamp used to expire cancelled orders."""
    inspector = inspect(engine)
    if "orders" not in inspector.get_table_names():
        return
    existing_columns = {column["name"] for column in inspector.get_columns("orders")}
    if "cancelled_at" not in existing_columns:
        with engine.begin() as connection:
            connection.execute(text(
                "ALTER TABLE orders ADD COLUMN cancelled_at TIMESTAMP WITH TIME ZONE"
            ))

def migrate_product_variant_fields():
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    additions = {
        "products": {"image_urls_json": "TEXT", "colors_json": "TEXT"},
        "cart_items": {"selected_color": "VARCHAR(80)"},
        "order_items": {"selected_color": "VARCHAR(80)"},
    }
    with engine.begin() as connection:
        for table, columns in additions.items():
            if table not in tables:
                continue
            existing = {column["name"] for column in inspector.get_columns(table)}
            for name, definition in columns.items():
                if name not in existing:
                    connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {definition}"))

def migrate_product_inventory_fields():
    inspector = inspect(engine)
    if "products" not in inspector.get_table_names():
        return
    existing_columns = {column["name"] for column in inspector.get_columns("products")}
    if "stock" not in existing_columns:
        with engine.begin() as connection:
            connection.execute(text(
                "ALTER TABLE products ADD COLUMN stock INTEGER NOT NULL DEFAULT 0"
            ))

def migrate_chat_message_fields():
    """Add attachment and read-state fields to existing support chats."""
    inspector = inspect(engine)
    if "chat_messages" not in inspector.get_table_names():
        return
    existing_columns = {column["name"] for column in inspector.get_columns("chat_messages")}
    required_columns = {
        "attachment_url": "VARCHAR(2048)",
        "read_at": "TIMESTAMP WITH TIME ZONE",
    }
    with engine.begin() as connection:
        for name, definition in required_columns.items():
            if name not in existing_columns:
                connection.execute(text(f"ALTER TABLE chat_messages ADD COLUMN {name} {definition}"))


def migrate_legacy_minio_urls():
    """Correct product image URLs created with the obsolete http://w hostname."""
    public_url = os.getenv("MINIO_PUBLIC_URL", "").rstrip("/")
    legacy_url = "http://w:9008/uploads"
    if not public_url or public_url == legacy_url:
        return

    from . import models

    db = SessionLocal()
    try:
        changed = False
        for product in db.query(models.Product).filter(
            models.Product.image_url.like(f"{legacy_url}/%")
        ).all():
            product.image_url = product.image_url.replace(legacy_url, public_url, 1)
            if product.image_urls_json:
                images = json.loads(product.image_urls_json)
                product.image_urls_json = json.dumps([
                    image.replace(legacy_url, public_url, 1) if image.startswith(legacy_url) else image
                    for image in images
                ])
            changed = True
        if changed:
            db.commit()
    finally:
        db.close()

def migrate_user_verification_fields():
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return
    existing_columns = {column["name"] for column in inspector.get_columns("users")}
    # Existing accounts predate verification, so preserve their ability to sign in.
    required_columns = {
        "email_verified": "BOOLEAN NOT NULL DEFAULT true",
        "email_verification_token": "VARCHAR(255)",
        "email_verification_expires_at": "TIMESTAMP WITH TIME ZONE",
    }
    with engine.begin() as connection:
        for name, definition in required_columns.items():
            if name not in existing_columns:
                connection.execute(text(f"ALTER TABLE users ADD COLUMN {name} {definition}"))

def migrate_user_profile_fields():
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return
    existing_columns = {column["name"] for column in inspector.get_columns("users")}
    if "name" not in existing_columns:
        with engine.begin() as connection:
            connection.execute(text(
                "ALTER TABLE users ADD COLUMN name VARCHAR(120) NOT NULL DEFAULT ''"
            ))
    existing_columns = {column["name"] for column in inspector.get_columns("users")}
    profile_columns = {
        "phone": "VARCHAR(40)",
        "delivery_address": "TEXT",
    }
    with engine.begin() as connection:
        for name, definition in profile_columns.items():
            if name not in existing_columns:
                connection.execute(text(f"ALTER TABLE users ADD COLUMN {name} {definition}"))
