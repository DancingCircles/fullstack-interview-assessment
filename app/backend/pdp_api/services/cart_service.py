from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from pdp_api.db.models import CartItem, IdempotencyRecord, Sku

DEMO_CART_ID = "demo-cart"
ADD_ITEM_SCOPE = f"cart:{DEMO_CART_ID}:POST:/api/cart/items"


@dataclass(frozen=True)
class ServiceResult:
    status_code: int
    body: dict
    replayed: bool = False


def add_item(
    session_factory,
    *,
    sku_id: str,
    quantity: int,
    idempotency_key: str,
) -> ServiceResult:
    request_hash = _request_hash(sku_id, quantity)

    try:
        with session_factory.begin() as session:
            record = IdempotencyRecord(
                scope=ADD_ITEM_SCOPE,
                key=idempotency_key,
                request_hash=request_hash,
            )
            session.add(record)
            session.flush()  # Atomic claim: competing requests cannot both proceed.

            result = _apply_add_item(session, sku_id, quantity)
            record.status_code = result.status_code
            record.response_json = json.dumps(result.body, separators=(",", ":"))
            return result
    except IntegrityError:
        # A duplicate key lost the unique-constraint race. The winning transaction
        # has committed by the time SQLite exposes the constraint violation.
        with session_factory() as session:
            record = session.scalar(
                select(IdempotencyRecord).where(
                    IdempotencyRecord.scope == ADD_ITEM_SCOPE,
                    IdempotencyRecord.key == idempotency_key,
                )
            )
            if record is None:
                raise
            if record.request_hash != request_hash:
                return _error(409, "IDEMPOTENCY_KEY_REUSED", "Idempotency-Key was used for a different request.")
            return ServiceResult(record.status_code or 500, json.loads(record.response_json or "{}"), replayed=True)


def get_cart(session: Session) -> dict:
    rows = session.execute(
        select(CartItem, Sku)
        .join(Sku, CartItem.sku_id == Sku.id)
        .where(CartItem.cart_id == DEMO_CART_ID)
        .order_by(CartItem.id)
    ).all()
    items = [
        {
            "sku_id": item.sku_id,
            "quantity": item.quantity,
            "unit_price_cents": sku.price_cents,
            "line_total_cents": sku.price_cents * item.quantity,
        }
        for item, sku in rows
    ]
    return {"cart_id": DEMO_CART_ID, "item_count": sum(item["quantity"] for item in items), "items": items}


def _apply_add_item(session: Session, sku_id: str, quantity: int) -> ServiceResult:
    reserve = session.execute(
        update(Sku)
        .where(Sku.id == sku_id, Sku.on_hand - Sku.reserved >= quantity)
        .values(reserved=Sku.reserved + quantity)
    )
    if reserve.rowcount != 1:
        sku = session.get(Sku, sku_id)
        if sku is None:
            return _error(404, "SKU_NOT_FOUND", "The selected SKU does not exist.")
        return _error(409, "OUT_OF_STOCK", "The selected quantity is no longer available.")

    cart_item = session.scalar(
        select(CartItem).where(CartItem.cart_id == DEMO_CART_ID, CartItem.sku_id == sku_id)
    )
    if cart_item is None:
        cart_item = CartItem(cart_id=DEMO_CART_ID, sku_id=sku_id, quantity=quantity)
        session.add(cart_item)
    else:
        cart_item.quantity += quantity
    session.flush()

    sku = session.get(Sku, sku_id)
    assert sku is not None
    body = {
        "cart": get_cart(session),
        "reserved_sku_id": sku_id,
        "available_quantity": sku.on_hand - sku.reserved,
    }
    return ServiceResult(201, body)


def _error(status_code: int, code: str, message: str) -> ServiceResult:
    return ServiceResult(status_code, {"error": {"code": code, "message": message}})


def _request_hash(sku_id: str, quantity: int) -> str:
    encoded = json.dumps({"sku_id": sku_id, "quantity": quantity}, sort_keys=True).encode()
    return hashlib.sha256(encoded).hexdigest()
