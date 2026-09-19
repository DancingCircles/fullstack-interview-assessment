from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from pdp_api.db.models import CartItem, Sku
from pdp_api.main import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'test.db'}")
    with TestClient(app) as test_client:
        yield test_client


def add_item(client: TestClient, key: str, quantity: int = 1):
    return client.post(
        "/api/cart/items",
        headers={"Idempotency-Key": key},
        json={"sku_id": "rr-mist-41", "quantity": quantity},
    )


def test_product_payload_contains_variants_and_available_stock(client: TestClient) -> None:
    response = client.get("/api/products/ridge-runner")

    assert response.status_code == 200
    payload = response.json()
    assert {option["id"] for option in payload["options"]} == {"color", "size"}
    assert len(payload["skus"]) == 6
    assert len(payload["images"]) == 3
    assert {image["url"] for image in payload["images"]} == {
        "/products/mist.png",
        "/products/graphite.png",
        "/products/clay.png",
    }
    assert next(sku for sku in payload["skus"] if sku["id"] == "rr-clay-41")["image_url"] == "/products/clay.png"
    assert next(sku for sku in payload["skus"] if sku["id"] == "rr-mist-42")["available_quantity"] == 0


def test_add_item_validates_and_returns_cart(client: TestClient) -> None:
    response = add_item(client, "add-1", quantity=2)

    assert response.status_code == 201
    assert response.json()["cart"]["item_count"] == 2
    assert response.json()["available_quantity"] == 1


def test_idempotent_replay_does_not_reserve_or_add_twice(client: TestClient) -> None:
    first = add_item(client, "retry-1")
    replay = add_item(client, "retry-1")

    assert first.status_code == replay.status_code == 201
    assert first.json() == replay.json()
    assert replay.headers["Idempotency-Replayed"] == "true"
    assert client.get("/api/cart").json()["item_count"] == 1


def test_same_idempotency_key_with_different_body_is_conflict(client: TestClient) -> None:
    add_item(client, "collision", quantity=1)
    response = add_item(client, "collision", quantity=2)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"


def test_invalid_input_and_missing_sku_return_structured_errors(client: TestClient) -> None:
    invalid = client.post(
        "/api/cart/items",
        headers={"Idempotency-Key": "bad-quantity"},
        json={"sku_id": "rr-mist-41", "quantity": 0},
    )
    missing = client.post(
        "/api/cart/items",
        headers={"Idempotency-Key": "unknown-sku"},
        json={"sku_id": "does-not-exist", "quantity": 1},
    )

    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "SKU_NOT_FOUND"


def test_concurrent_requests_for_last_unit_do_not_oversell(client: TestClient) -> None:
    database = client.app.state.database
    with database.session_factory.begin() as session:
        sku = session.get(Sku, "rr-mist-41")
        assert sku is not None
        sku.on_hand = 1
        sku.reserved = 0

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(lambda key: add_item(client, key), ["race-a", "race-b"]))

    assert sorted(response.status_code for response in responses) == [201, 409]
    with database.session_factory() as session:
        sku = session.get(Sku, "rr-mist-41")
        cart_items = session.scalars(select(CartItem).where(CartItem.sku_id == "rr-mist-41")).all()
        assert sku is not None
        assert (sku.on_hand, sku.reserved) == (1, 1)
        assert sum(item.quantity for item in cart_items) == 1
