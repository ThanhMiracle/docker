from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import os
from . import database, models, crud, schemas, security, storage
from .deps import get_current_user

app = FastAPI(title="Simple Shop API (v3-fix)")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
models.Base.metadata.create_all(bind=database.engine)

@app.get("/health")
def health(): return {"status":"ok"}

@app.post("/auth/register", response_model=schemas.UserOut)
def register(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    existed = crud.get_user_by_email(db, user.email)
    if existed: raise HTTPException(400, "Email already registered")
    return crud.create_user(db, email=user.email, password=user.password)

@app.post("/auth/login", response_model=schemas.Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    user = crud.get_user_by_email(db, form.username)
    if not user or not security.verify_password(form.password, user.hashed_password):
        raise HTTPException(400, "Incorrect email or password")
    token = security.create_access_token({"sub": user.email})
    return {"access_token": token, "token_type":"bearer"}

@app.post("/auth/logout")
def logout(user=Depends(get_current_user)): return {"ok": True}

@app.post("/files/upload")
async def upload_file(file: UploadFile = File(...), user=Depends(get_current_user)):
    data = await file.read()
    if not data: raise HTTPException(400, "Empty file")
    import os as _os
    ext = _os.path.splitext(file.filename or "")[1]
    url = storage.put_file(data, file.content_type or "application/octet-stream", ext=ext)
    return {"url": url}

@app.post("/products/", response_model=schemas.ProductOut)
def create_product(product: schemas.ProductCreate, db: Session = Depends(database.get_db), user=Depends(get_current_user)):
    return crud.create_product(db, product.dict(), owner_id=user.id)

@app.get("/products/", response_model=schemas.ProductsPage)
def list_products(skip:int=0, limit:int=12, q:str|None=None, db: Session = Depends(database.get_db)):
    items, total = crud.list_products(db, skip=skip, limit=limit, q=q)
    return {"items":items, "total":total, "skip":skip, "limit":limit, "q":q}

@app.get("/products/mine", response_model=schemas.ProductsPage)
def my_products(skip:int=0, limit:int=12, q:str|None=None, db: Session = Depends(database.get_db), user=Depends(get_current_user)):
    items, total = crud.list_my_products(db, owner_id=user.id, skip=skip, limit=limit, q=q)
    return {"items":items, "total":total, "skip":skip, "limit":limit, "q":q}

@app.get("/products/{pid}", response_model=schemas.ProductOut)
def get_product(pid:int, db: Session = Depends(database.get_db)):
    p = crud.get_product(db, pid)
    if not p: raise HTTPException(404, "Not found")
    return p

@app.put("/products/{pid}", response_model=schemas.ProductOut)
def update_product(pid:int, product: schemas.ProductCreate, db: Session = Depends(database.get_db), user=Depends(get_current_user)):
    p, err = crud.update_product(db, pid, product.dict(), requester_id=user.id, admin=user.is_admin)
    if err == "not_found": raise HTTPException(404, "Not found")
    if err == "forbidden": raise HTTPException(403, "Forbidden: only owner can edit")
    return p

@app.delete("/products/{pid}")
def delete_product(pid:int, db: Session = Depends(database.get_db), user=Depends(get_current_user)):
    p, err = crud.delete_product(db, pid, requester_id=user.id, admin=user.is_admin)
    if err == "not_found": raise HTTPException(404, "Not found")
    if err == "forbidden": raise HTTPException(403, "Forbidden: only owner can delete")
    return {"ok": True}
