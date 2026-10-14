"""Verified-purchase reviews with configurable media storage."""

import logging

from azure.core.exceptions import AzureError, ResourceNotFoundError
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from starlette.concurrency import run_in_threadpool

from . import database, models, schemas, storage
from .deps import get_current_user

router = APIRouter()
logger = logging.getLogger("shop.reviews")
MAX_ATTACHMENTS = 6
IMAGE_LIMIT = 5 * 1024 * 1024
VIDEO_LIMIT = 30 * 1024 * 1024
TOTAL_LIMIT = 40 * 1024 * 1024
MEDIA_TYPES = {
    "image/jpeg": ("image", ".jpg", IMAGE_LIMIT),
    "image/png": ("image", ".png", IMAGE_LIMIT),
    "image/webp": ("image", ".webp", IMAGE_LIMIT),
    "image/gif": ("image", ".gif", IMAGE_LIMIT),
    "video/mp4": ("video", ".mp4", VIDEO_LIMIT),
    "video/webm": ("video", ".webm", VIDEO_LIMIT),
}


def matches_media_type(data, content_type):
    """Check the file signature rather than trusting a client filename/MIME type."""
    return {
        "image/jpeg": data.startswith(b"\xff\xd8\xff"),
        "image/png": data.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/gif": data.startswith((b"GIF87a", b"GIF89a")),
        "image/webp": data[:4] == b"RIFF" and data[8:12] == b"WEBP",
        "video/mp4": len(data) >= 12 and data[4:8] == b"ftyp",
        "video/webm": data.startswith(b"\x1a\x45\xdf\xa3"),
    }.get(content_type, False)


def require_product(db, pid):
    if not db.get(models.Product, pid):
        raise HTTPException(status_code=404, detail="Product not found")


@router.get("/products/{pid}/reviews", response_model=schemas.ReviewsPage)
def list_reviews(
    pid: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(database.get_db),
):
    require_product(db, pid)
    query = db.query(models.ProductReview).filter(models.ProductReview.product_id == pid)
    total, average = query.with_entities(func.count(models.ProductReview.id), func.avg(models.ProductReview.rating)).one()
    return {
        "items": query.options(selectinload(models.ProductReview.media))
            .order_by(models.ProductReview.id.desc()).offset(skip).limit(limit).all(),
        "total": total, "average_rating": round(average, 1) if average is not None else None,
        "skip": skip, "limit": limit,
    }


@router.get("/products/{pid}/review-eligibility", response_model=schemas.ReviewEligibility)
def review_eligibility(pid: int, db: Session = Depends(database.get_db), user=Depends(get_current_user)):
    require_product(db, pid)
    if user.is_admin:
        return {"eligible_orders": []}
    orders = db.query(models.Order).filter(
        models.Order.user_id == user.id,
        models.Order.status == "delivered",
        models.Order.items.any(product_id=pid),
        ~models.Order.reviews.any(product_id=pid),
    ).order_by(models.Order.id.desc()).all()
    return {"eligible_orders": [{"order_id": order.id, "created_at": order.created_at} for order in orders]}


@router.post("/products/{pid}/reviews", response_model=schemas.ReviewOut, status_code=201)
async def create_review(
    pid: int,
    order_id: int = Form(..., gt=0),
    rating: int = Form(..., ge=1, le=5),
    comment: str = Form(..., min_length=1, max_length=3000),
    files: list[UploadFile] = File(default=[]),
    db: Session = Depends(database.get_db),
    user=Depends(get_current_user),
):
    require_product(db, pid)
    if user.is_admin:
        raise HTTPException(status_code=403, detail="Only customers can write product reviews")
    order = db.query(models.Order).filter(models.Order.id == order_id, models.Order.user_id == user.id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != "delivered":
        raise HTTPException(status_code=403, detail="Reviews are available after your order is delivered")
    if not any(item.product_id == pid for item in order.items):
        raise HTTPException(status_code=403, detail="This product is not in your delivered order")
    if any(review.product_id == pid for review in order.reviews):
        raise HTTPException(status_code=409, detail="You already reviewed this product for this order")
    comment = comment.strip()
    if not comment:
        raise HTTPException(status_code=422, detail="Please write a review comment")
    if len(files) > MAX_ATTACHMENTS:
        raise HTTPException(status_code=400, detail="Attach up to 6 photos or videos")

    # Validate every attachment before reserving a review or writing any blob.
    attachments, total_size = [], 0
    for file in files:
        content_type = (file.content_type or "").lower()
        if content_type not in MEDIA_TYPES:
            raise HTTPException(status_code=400, detail="Use JPEG, PNG, WebP, GIF, MP4 or WebM files")
        kind, ext, limit = MEDIA_TYPES[content_type]
        data = await file.read(limit + 1)
        if not data:
            raise HTTPException(status_code=400, detail="Attachments must not be empty")
        if len(data) > limit:
            raise HTTPException(status_code=413, detail="Photos must be at most 5 MB; videos at most 30 MB")
        total_size += len(data)
        if total_size > TOTAL_LIMIT:
            raise HTTPException(status_code=413, detail="Attachments must total at most 40 MB")
        if not matches_media_type(data, content_type):
            raise HTTPException(status_code=400, detail="An attachment does not match its file type")
        attachments.append((data, content_type, kind, ext))

    review = models.ProductReview(
        order_id=order_id, product_id=pid, user_id=user.id, author_name=user.name or "Customer",
        rating=rating, comment=comment,
    )
    uploaded_keys = []
    try:
        db.add(review)
        # The unique constraint prevents duplicate submissions, including races.
        db.flush()
        for data, content_type, kind, ext in attachments:
            key, url = await run_in_threadpool(storage.put_review_file, data, content_type, ext)
            uploaded_keys.append(key)
            review.media.append(models.ReviewMedia(blob_key=key, url=url, kind=kind, content_type=content_type))
        db.commit()
    except Exception as error:
        db.rollback()
        for key in uploaded_keys:
            try:
                await run_in_threadpool(storage.delete_review_file, key)
            except Exception:
                logger.exception("Could not clean up a failed review upload")
        if isinstance(error, IntegrityError):
            raise HTTPException(status_code=409, detail="You already reviewed this product for this order")
        logger.exception("Could not save product review")
        if isinstance(error, storage.StorageConfigurationError):
            raise HTTPException(
                status_code=503,
                detail="Photo and video uploads are currently unavailable. Remove the attachments to publish a text-only review.",
            )
        raise HTTPException(status_code=503, detail="Could not save your review. Please try again.")
    db.refresh(review)
    return review


def read_review_media(key, range_header=None):
    try:
        chunks, content_type, total, start, end = storage.get_review_media(key, range_header)
    except storage.InvalidMediaRange as error:
        raise HTTPException(status_code=416, detail="Requested range is not available", headers={"Content-Range": f"bytes */{error.total}"})
    except (ValueError, ResourceNotFoundError):
        raise HTTPException(status_code=404, detail="Review media not found")
    except ClientError as error:
        if error.response.get("Error", {}).get("Code") in {"NoSuchKey", "NotFound", "404"}:
            raise HTTPException(status_code=404, detail="Review media not found")
        logger.exception("Review media read failed")
        raise HTTPException(status_code=503, detail="Review media storage unavailable")
    except (AzureError, BotoCoreError, RuntimeError):
        logger.exception("Review media read failed")
        raise HTTPException(status_code=503, detail="Review media storage unavailable")
    headers = {
        "Content-Length": str(end - start + 1), "Accept-Ranges": "bytes",
        "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "sandbox; default-src 'none'",
    }
    if range_header:
        headers["Content-Range"] = f"bytes {start}-{end}/{total}"
    return StreamingResponse(chunks, media_type=content_type, headers=headers, status_code=206 if range_header else 200)
