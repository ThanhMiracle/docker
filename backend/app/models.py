import json
from sqlalchemy import Column, Integer, String, Float, Text, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False)
    email_verified = Column(Boolean, default=False, nullable=False)
    email_verification_token = Column(String, unique=True, nullable=True, index=True)
    email_verification_expires_at = Column(DateTime(timezone=True), nullable=True)
    products = relationship("Product", back_populates="owner", cascade="all, delete-orphan")
    cart_items = relationship("CartItem", back_populates="user", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    price = Column(Float, nullable=False)
    image_url = Column(String, nullable=True)
    image_urls_json = Column(Text, nullable=True)
    colors_json = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="products")

    @property
    def images(self):
        return json.loads(self.image_urls_json) if self.image_urls_json else ([self.image_url] if self.image_url else [])

    @property
    def colors(self):
        return json.loads(self.colors_json) if self.colors_json else []

class CartItem(Base):
    __tablename__ = "cart_items"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    selected_color = Column(String, nullable=True)
    quantity = Column(Integer, nullable=False, default=1)
    user = relationship("User", back_populates="cart_items")
    product = relationship("Product")

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    total = Column(Float, nullable=False)
    customer_name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    delivery_address = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="pending_confirmation")
    confirmation_token = Column(String, unique=True, nullable=True, index=True)
    confirmation_expires_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    product_id = Column(Integer, nullable=False)
    product_name = Column(String, nullable=False)
    unit_price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    selected_color = Column(String, nullable=True)
    order = relationship("Order", back_populates="items")
