from pydantic import BaseModel, EmailStr
from typing import Optional, List
from pydantic import ConfigDict
class UserCreate(BaseModel):
    email: EmailStr
    password: str
class UserOut(BaseModel):
    id: int
    email: EmailStr
    is_admin: bool
    model_config = ConfigDict(from_attributes=True) 
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
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
