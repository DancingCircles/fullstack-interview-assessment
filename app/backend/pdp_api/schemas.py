from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CartAddRequest(BaseModel):
    sku_id: str = Field(min_length=1, max_length=80)
    quantity: int = Field(ge=1, le=99)


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody


class CartItemResponse(BaseModel):
    sku_id: str
    quantity: int
    unit_price_cents: int
    line_total_cents: int


class CartResponse(BaseModel):
    cart_id: str
    item_count: int
    items: list[CartItemResponse]


class AddCartResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cart: CartResponse
    reserved_sku_id: str
    available_quantity: int

