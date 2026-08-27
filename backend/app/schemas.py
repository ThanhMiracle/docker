from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from pydantic import ConfigDict
class UserCreate(BaseModel):
    email: EmailStr
    password: str
class UserOut(BaseModel):
    id: int
    email: EmailStr
    is_admin: bool
    email_verified: bool
    model_config = ConfigDict(from_attributes=True) 
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    is_admin: bool = False
class EmailToken(BaseModel):
    token: str = Field(min_length=20)
class ProductBase(BaseModel):
    name: str
    price: float
    image_url: Optional[str] = None
    description: Optional[str] = None
class ProductCreate(ProductBase): pass
class ProductOut(ProductBase):
    id: int
    owner_id: int
    model_config = ConfigDict(from_attributes=True) 
class ProductsPage(BaseModel):
    items: List[ProductOut]
    total: int
    skip: int
    limit: int
    q: Optional[str] = None

class CartItemCreate(BaseModel):
    product_id: int
    quantity: int = 1

class CartItemUpdate(BaseModel):
    quantity: int

class CartItemOut(BaseModel):
    product_id: int
    quantity: int
    product: ProductOut
    model_config = ConfigDict(from_attributes=True)

class CartOut(BaseModel):
    items: List[CartItemOut]
    total: float

class OrderItemOut(BaseModel):
    product_id: int
    product_name: str
    unit_price: float
    quantity: int
    model_config = ConfigDict(from_attributes=True)

class CheckoutCreate(BaseModel):
    customer_name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=3, max_length=40)
    delivery_address: str = Field(min_length=5, max_length=500)

class OrderDeliveryUpdate(BaseModel):
    phone: str = Field(min_length=3, max_length=40)
    delivery_address: str = Field(min_length=5, max_length=500)

class ConfirmOrder(BaseModel):
    token: str = Field(min_length=20)

class OrderOut(BaseModel):
    id: int
    total: float
    customer_name: str
    phone: str
    delivery_address: str
    status: str
    created_at: datetime
    items: List[OrderItemOut]
    model_config = ConfigDict(from_attributes=True)
