from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from . import models, security
def create_user(db: Session, email: str, password: str, is_admin: bool = False):
    user = models.User(email=email, hashed_password=security.get_password_hash(password), is_admin=is_admin)
    db.add(user); db.commit(); db.refresh(user); return user
def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()
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
