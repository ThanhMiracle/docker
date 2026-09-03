from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import os
import json
import logging
import time
import uuid

from . import database, models, crud, schemas, security, storage, email_service, rate_limit
from .chat_realtime import chat_connections
from .observability import configure_logging
from .deps import get_current_user, get_current_admin


configure_logging()
logger = logging.getLogger("shop.api")
app = FastAPI(title="Simple Shop API (v3-fix)")

cors_origins = [
    origin.strip() for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost,http://localhost:3000,http://localhost:8080"
    ).split(",") if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex)
    started = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    logger.info(json.dumps({
        "event": "request", "request_id": request_id,
        "method": request.method, "path": request.url.path,
        "status": response.status_code,
        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
    }))
    return response

models.Base.metadata.create_all(bind=database.engine)
database.migrate_order_delivery_fields()
database.migrate_order_confirmation_fields()
database.migrate_order_cancellation_fields()
database.migrate_product_variant_fields()
database.migrate_product_inventory_fields()
database.migrate_user_verification_fields()
database.migrate_user_profile_fields()
database.migrate_chat_message_fields()
database.migrate_legacy_minio_urls()
database.configure_single_admin(os.getenv("ADMIN_EMAIL"))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/profile", response_model=schemas.UserProfileOut)
def get_profile(user=Depends(get_current_user)):
    return user


@app.put("/profile", response_model=schemas.UserProfileOut)
def update_profile(
    data: schemas.UserProfileUpdate,
    db: Session = Depends(database.get_db),
    user=Depends(get_current_user),
):
    return crud.update_user_profile(db, user, data.model_dump())


# =========================
# AUTH
# =========================

@app.post("/auth/register", response_model=schemas.UserOut)
def register(
    user: schemas.UserCreate,
    db: Session = Depends(database.get_db),
):
    email = user.email.strip().lower()

    existed = crud.get_user_by_email(db, email)

    if existed:
        raise HTTPException(
            status_code=400,
            detail="Email already registered",
        )

    admin_email = os.getenv("ADMIN_EMAIL", "").strip().lower()

    is_admin = bool(admin_email) and email == admin_email

    # Ensure only one admin exists
    if is_admin:
        db.query(models.User).filter(
            models.User.is_admin.is_(True)
        ).update(
            {"is_admin": False},
            synchronize_session=False,
        )

        db.commit()

    created_user = crud.create_user(
        db=db,
        name=user.name,
        email=email,
        password=user.password,
        is_admin=is_admin,
    )

    # Normal users need email verification.
    # Admin is automatically verified.
    if not is_admin:
        try:
            email_service.send_account_verification(
                created_user.email,
                created_user.email_verification_token,
            )

        except RuntimeError as error:
            raise HTTPException(
                status_code=503,
                detail=str(error),
            )

        except Exception:
            raise HTTPException(
                status_code=503,
                detail="Could not send verification email. Please try again later.",
            )

    return created_user


@app.post("/auth/login", response_model=schemas.Token)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(database.get_db),
    request: Request = None,
):
    client_ip = request.client.host if request and request.client else "unknown"
    if not rate_limit.allow_login(client_ip):
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again shortly.")
    email = form.username.strip().lower()

    user = crud.get_user_by_email(db, email)

    if not user or not security.verify_password(
        form.password,
        user.hashed_password,
    ):
        rate_limit.record_failed_login(client_ip)
        raise HTTPException(
            status_code=400,
            detail="Incorrect email or password",
        )

    # Administrators are allowed to sign in without email verification.
    # This also covers an existing admin account that predates the automatic
    # verification setup.
    if not user.is_admin and not user.email_verified:
        raise HTTPException(
            status_code=403,
            detail="Please confirm your email before logging in",
        )

    token = security.create_access_token(
        {"sub": user.email}
    )
    rate_limit.clear_login_attempts(client_ip)

    return {
        "access_token": token,
        "token_type": "bearer",
        "is_admin": user.is_admin,
    }


@app.post("/auth/verify-email", response_model=schemas.UserOut)
def verify_email(
    data: schemas.EmailToken,
    db: Session = Depends(database.get_db),
):
    user, error = crud.verify_user_email(
        db,
        data.token,
    )

    if error == "invalid":
        raise HTTPException(
            status_code=404,
            detail="Verification link is invalid or has already been used",
        )

    if error == "expired":
        raise HTTPException(
            status_code=400,
            detail="Verification link has expired",
        )

    return user


@app.post("/auth/logout")
def logout(user=Depends(get_current_user)):
    return {"ok": True}


# =========================
# FILES
# =========================

@app.post("/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    user=Depends(get_current_admin),
):
    data = await file.read()

    if not data:
        raise HTTPException(
            status_code=400,
            detail="Empty file",
        )

    ext = os.path.splitext(
        file.filename or ""
    )[1]

    url = storage.put_file(
        data,
        file.content_type or "application/octet-stream",
        ext=ext,
    )

    return {"url": url}


@app.post("/chat/files/upload")
async def upload_chat_image(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image attachments are allowed")
    data = await file.read()
    if not data or len(data) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image must be between 1 byte and 5 MB")
    ext = os.path.splitext(file.filename or "")[1]
    return {"url": storage.put_file(data, file.content_type, ext=ext)}


# =========================
# PRODUCTS
# =========================

@app.post("/products/", response_model=schemas.ProductOut)
def create_product(
    product: schemas.ProductCreate,
    db: Session = Depends(database.get_db),
    user=Depends(get_current_admin),
):
    return crud.create_product(
        db,
        product.model_dump(),
        owner_id=user.id,
    )


@app.get("/products/", response_model=schemas.ProductsPage)
def list_products(
    skip: int = 0,
    limit: int = 12,
    q: str | None = None,
    db: Session = Depends(database.get_db),
):
    items, total = crud.list_products(
        db,
        skip=skip,
        limit=limit,
        q=q,
    )

    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit,
        "q": q,
    }


@app.get("/products/mine", response_model=schemas.ProductsPage)
def my_products(
    skip: int = 0,
    limit: int = 12,
    q: str | None = None,
    db: Session = Depends(database.get_db),
    user=Depends(get_current_user),
):
    items, total = crud.list_my_products(
        db,
        owner_id=user.id,
        skip=skip,
        limit=limit,
        q=q,
    )

    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit,
        "q": q,
    }


@app.get("/products/{pid}", response_model=schemas.ProductOut)
def get_product(
    pid: int,
    db: Session = Depends(database.get_db),
):
    product = crud.get_product(db, pid)

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Not found",
        )

    return product


@app.put("/products/{pid}", response_model=schemas.ProductOut)
def update_product(
    pid: int,
    product: schemas.ProductCreate,
    db: Session = Depends(database.get_db),
    user=Depends(get_current_user),
):
    updated_product, error = crud.update_product(
        db,
        pid,
        product.model_dump(),
        requester_id=user.id,
        admin=user.is_admin,
    )

    if error == "not_found":
        raise HTTPException(
            status_code=404,
            detail="Not found",
        )

    if error == "forbidden":
        raise HTTPException(
            status_code=403,
            detail="Forbidden: only owner can edit",
        )

    return updated_product


@app.delete("/products/{pid}")
def delete_product(
    pid: int,
    db: Session = Depends(database.get_db),
    user=Depends(get_current_admin),
):
    product, error = crud.delete_product(
        db,
        pid,
        requester_id=user.id,
        admin=user.is_admin,
    )

    if error == "not_found":
        raise HTTPException(
            status_code=404,
            detail="Not found",
        )

    if error == "forbidden":
        raise HTTPException(
            status_code=403,
            detail="Forbidden: only owner can delete",
        )

    return {"ok": True}


# =========================
# CART
# =========================

def cart_response(
    db: Session,
    user_id: int,
):
    items = crud.get_cart_items(
        db,
        user_id,
    )

    total = sum(
        item.product.price * item.quantity
        for item in items
    )

    return {
        "items": items,
        "total": total,
    }


@app.get("/cart", response_model=schemas.CartOut)
def get_cart(
    db: Session = Depends(database.get_db),
    user=Depends(get_current_user),
):
    return cart_response(
        db,
        user.id,
    )


@app.post("/cart/items", response_model=schemas.CartOut)
def add_to_cart(
    item: schemas.CartItemCreate,
    db: Session = Depends(database.get_db),
    user=Depends(get_current_user),
):
    if item.quantity < 1:
        raise HTTPException(
            status_code=400,
            detail="Quantity must be at least 1",
        )

    if not crud.get_product(
        db,
        item.product_id,
    ):
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    available = crud.available_stock_for_cart_item(
        db, user.id, item.product_id, item.selected_color
    )
    if item.quantity > available:
        raise HTTPException(status_code=400, detail="Not enough stock available")

    crud.add_cart_item(
        db,
        user.id,
        item.product_id,
        item.quantity,
        item.selected_color,
    )

    return cart_response(
        db,
        user.id,
    )


@app.put(
    "/cart/items/{product_id}",
    response_model=schemas.CartOut,
)
def update_cart_item(
    product_id: int,
    item: schemas.CartItemUpdate,
    db: Session = Depends(database.get_db),
    user=Depends(get_current_user),
):
    if item.quantity < 1:
        raise HTTPException(
            status_code=400,
            detail="Quantity must be at least 1",
        )

    if not crud.can_set_cart_quantity(
        db, user.id, product_id, item.selected_color, item.quantity
    ):
        raise HTTPException(status_code=400, detail="Not enough stock available")

    updated = crud.update_cart_item(
        db,
        user.id,
        product_id,
        item.quantity,
        item.selected_color,
    )

    if not updated:
        raise HTTPException(
            status_code=404,
            detail="Cart item not found",
        )

    return cart_response(
        db,
        user.id,
    )


@app.delete(
    "/cart/items/{product_id}",
    response_model=schemas.CartOut,
)
def remove_cart_item(
    product_id: int,
    selected_color: str | None = None,
    db: Session = Depends(database.get_db),
    user=Depends(get_current_user),
):
    removed = crud.remove_cart_item(
        db,
        user.id,
        product_id,
        selected_color,
    )

    if not removed:
        raise HTTPException(
            status_code=404,
            detail="Cart item not found",
        )

    return cart_response(
        db,
        user.id,
    )


# =========================
# CHECKOUT / ORDERS
# =========================

@app.post(
    "/cart/checkout",
    response_model=schemas.OrderOut,
)
def checkout(
    checkout_data: schemas.CheckoutCreate,
    db: Session = Depends(database.get_db),
    user=Depends(get_current_user),
):
    order = crud.checkout_cart(
        db,
        user.id,
        checkout_data.model_dump(),
    )

    if not order:
        raise HTTPException(
            status_code=400,
            detail="Your cart is empty",
        )

    try:
        email_service.send_order_confirmation(
            user.email,
            order.id,
            order.confirmation_token,
        )

    except RuntimeError as error:
        raise HTTPException(
            status_code=503,
            detail=str(error),
        )

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Could not send confirmation email. Please try again later.",
        )

    return order


@app.post(
    "/orders/confirm",
    response_model=schemas.OrderOut,
)
def confirm_order(
    data: schemas.ConfirmOrder,
    db: Session = Depends(database.get_db),
):
    order, error = crud.confirm_order(
        db,
        data.token,
    )

    if error == "invalid":
        raise HTTPException(
            status_code=404,
            detail="Confirmation link is invalid or has already been used",
        )

    if error == "expired":
        raise HTTPException(
            status_code=400,
            detail="Confirmation link has expired",
        )

    if error == "out_of_stock":
        raise HTTPException(status_code=409, detail="One or more products are out of stock")

    return order


@app.post(
    "/orders/{order_id}/cancel",
    response_model=schemas.OrderOut,
)
def cancel_order(
    order_id: int,
    db: Session = Depends(database.get_db),
    user=Depends(get_current_user),
):
    order, error = crud.cancel_order(db, order_id, user.id)

    if error == "not_found":
        raise HTTPException(
            status_code=404,
            detail="Order not found",
        )
    if error == "cannot_cancel":
        raise HTTPException(
            status_code=400,
            detail="This order can no longer be cancelled",
        )

    return order


@app.put(
    "/orders/{order_id}/delivery",
    response_model=schemas.OrderOut,
)
def update_order_delivery(
    order_id: int,
    data: schemas.OrderDeliveryUpdate,
    db: Session = Depends(database.get_db),
    user=Depends(get_current_user),
):
    order, error = crud.update_order_delivery(
        db, order_id, user.id, data.model_dump()
    )

    if error == "not_found":
        raise HTTPException(status_code=404, detail="Order not found")
    if error == "cannot_update":
        raise HTTPException(
            status_code=400,
            detail="Cancelled orders cannot be updated",
        )

    return order


@app.get(
    "/orders/mine",
    response_model=list[schemas.OrderOut],
)
def my_orders(
    db: Session = Depends(database.get_db),
    user=Depends(get_current_user),
):
    crud.delete_expired_cancelled_orders(db, user.id)

    return (
        db.query(models.Order)
        .filter(models.Order.user_id == user.id)
        .order_by(models.Order.id.desc())
        .all()
    )


@app.get("/orders", response_model=list[schemas.OrderOut])
def all_orders(
    db: Session = Depends(database.get_db),
    user=Depends(get_current_admin),
):
    return db.query(models.Order).order_by(models.Order.id.desc()).all()


@app.put("/orders/{order_id}/status", response_model=schemas.OrderOut)
def update_order_status(
    order_id: int,
    data: schemas.OrderStatusUpdate,
    db: Session = Depends(database.get_db),
    user=Depends(get_current_admin),
):
    order, error = crud.update_order_status(db, order_id, data.status)
    if error == "not_found":
        raise HTTPException(status_code=404, detail="Order not found")
    if error == "invalid_transition":
        raise HTTPException(
            status_code=400,
            detail="Orders must move through confirmed, preparing, shipping, and delivered in order",
        )
    return order


# =========================
# CUSTOMER SUPPORT CHAT
# =========================

@app.get("/chat/messages", response_model=list[schemas.ChatMessageOut])
def get_chat_messages(
    db: Session = Depends(database.get_db),
    user=Depends(get_current_user),
):
    return crud.list_chat_messages(db, user)


@app.get("/chat/conversations", response_model=list[schemas.ChatConversationOut])
def get_chat_conversations(
    db: Session = Depends(database.get_db),
    user=Depends(get_current_admin),
):
    return crud.list_chat_conversations(db)


@app.get("/chat/unread", response_model=schemas.ChatUnreadOut)
def get_chat_unread_count(
    db: Session = Depends(database.get_db),
    user=Depends(get_current_user),
):
    return {"unread_count": crud.chat_unread_count(db, user)}


@app.post("/chat/read")
def mark_chat_read(
    customer_id: int | None = None,
    db: Session = Depends(database.get_db),
    user=Depends(get_current_user),
):
    error = crud.mark_chat_read(db, user, customer_id)
    if error == "customer_required":
        raise HTTPException(status_code=400, detail="Choose a customer conversation")
    return {"ok": True}


@app.post("/chat/messages", response_model=schemas.ChatMessageOut)
async def send_chat_message(
    data: schemas.ChatMessageCreate,
    db: Session = Depends(database.get_db),
    user=Depends(get_current_user),
):
    if not data.body.strip() and not data.attachment_url:
        raise HTTPException(status_code=400, detail="Write a message or attach an image")
    message, error = crud.create_chat_message(
        db, user, data.body, data.customer_id, data.attachment_url
    )
    if error == "customer_required":
        raise HTTPException(status_code=400, detail="Choose a customer to reply to")
    if error == "customer_not_found":
        raise HTTPException(status_code=404, detail="Customer not found")
    recipients = [message.customer_id]
    if not user.is_admin:
        recipients.extend(admin.id for admin in db.query(models.User).filter(
            models.User.is_admin.is_(True)
        ).all())
    await chat_connections.notify(recipients, {
        "type": "chat_message",
        "message": schemas.ChatMessageOut.model_validate(message).model_dump(mode="json"),
    })
    return message


@app.websocket("/chat/ws")
async def chat_websocket(websocket: WebSocket, token: str):
    """Send real-time chat events to the authenticated browser session."""
    try:
        payload = security.decode_token(token)
        email = payload.get("sub")
        if not email:
            raise ValueError("Missing subject")
        db = database.SessionLocal()
        user = db.query(models.User).filter(models.User.email == email).first()
        if not user:
            raise ValueError("User not found")
        user_id = user.id
    except Exception:
        await websocket.close(code=1008)
        return
    finally:
        if "db" in locals():
            db.close()

    await chat_connections.connect(user_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        chat_connections.disconnect(user_id, websocket)
