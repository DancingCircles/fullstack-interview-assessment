from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from pdp_api.db.database import Database
from pdp_api.db.models import Product, Sku
from pdp_api.schemas import CartAddRequest
from pdp_api.services.cart_service import add_item, get_cart

router = APIRouter(prefix="/api")


def get_database(request: Request) -> Database:
    return request.app.state.database


def get_session(database: Database = Depends(get_database)):
    yield from database.session()


@router.get("/products/{product_id}")
def get_product(product_id: str, session: Session = Depends(get_session)) -> dict:
    product = session.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    skus = session.scalars(select(Sku).where(Sku.product_id == product_id).order_by(Sku.id)).all()
    colors = ["Mist", "Graphite", "Clay"]
    sizes = ["40", "41", "42"]
    images = [
        {"id": "mist", "url": "/products/mist.png"},
        {"id": "graphite", "url": "/products/graphite.png"},
        {"id": "clay", "url": "/products/clay.png"},
    ]
    return {
        "id": product.id,
        "name": product.name,
        "description": product.description,
        "options": [
            {"id": "color", "label": "Color", "values": colors},
            {"id": "size", "label": "Size", "values": sizes},
        ],
        "images": images,
        "skus": [
            {
                "id": sku.id,
                "option_values": {"color": sku.color, "size": sku.size},
                "price_cents": sku.price_cents,
                "available_quantity": sku.on_hand - sku.reserved,
                # Derive the asset from the server-owned SKU colour so old
                # local seed databases also pick up the new product photos.
                "image_url": f"/products/{sku.color.lower()}.png",
            }
            for sku in skus
        ],
    }


@router.post("/cart/items")
def post_cart_item(
    body: CartAddRequest,
    database: Database = Depends(get_database),
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
) -> JSONResponse:
    result = add_item(
        database.session_factory,
        sku_id=body.sku_id,
        quantity=body.quantity,
        idempotency_key=idempotency_key,
    )
    headers = {"Idempotency-Replayed": "true"} if result.replayed else {}
    return JSONResponse(status_code=result.status_code, content=result.body, headers=headers)


@router.get("/cart")
def get_current_cart(session: Session = Depends(get_session)) -> dict:
    return get_cart(session)
