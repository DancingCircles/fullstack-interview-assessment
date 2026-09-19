# Ridge Runner — Full-stack interview assessment

A deliberately small, production-minded product-detail page plus three independent assessment tasks. The repository favours correctness, explainable trade-offs, and a fast reviewer setup over unnecessary e-commerce features.

## What is included

| Directory | Deliverable |
| --- | --- |
| `A/` | Deterministic, idempotent inventory reservation ledger and tests |
| `B/` | Exact warehouse-split optimiser and tests |
| `C/` | Xero multi-tenant integration design |
| `app/backend/` | FastAPI + SQLite PDP API, seed data, API tests |
| `app/frontend/` | Vite, React, TypeScript PDP and UI tests |

## Prerequisites

- Python 3.11 or newer (tested with 3.12)
- Node.js 20 or newer (tested with 24)
- npm 10 or newer

## Quick start

From the repository root:

```powershell
python -m pip install -e ".[dev]"
python -m pytest
```

Start the API in a first terminal:

```powershell
Set-Location app/backend
python -m uvicorn pdp_api.main:app --reload --port 8000
```

Start the frontend in a second terminal:

```powershell
Set-Location app/frontend
npm install
npm run dev
```

Open the URL printed by Vite (normally `http://localhost:5173`). The Vite development server proxies `/api` and `/products` to FastAPI, so no local CORS configuration is needed.

## Test and build commands

```powershell
# Root: Tasks A/B and FastAPI API tests
python -m pytest

# Frontend
Set-Location app/frontend
npm test
npm run lint
npm run build
```

Task A and B also run as command-line programs:

```powershell
python -m A.reservation_ledger < input.txt
python -m B.fulfillment_optimizer < input.txt
```

## PDP API contract

### `GET /api/products/ridge-runner`

Returns product options and the server-authoritative SKU price, image and available stock. A client never submits a price or stock count.

### `POST /api/cart/items`

Required header: `Idempotency-Key`.

```http
POST /api/cart/items
Content-Type: application/json
Idempotency-Key: 5b6be936-0364-4dc6-80bc-3b65546cc9d3

{"sku_id":"rr-mist-41","quantity":2}
```

Successful response (`201`):

```json
{
  "cart": {
    "cart_id": "demo-cart",
    "item_count": 2,
    "items": [
      {
        "sku_id": "rr-mist-41",
        "quantity": 2,
        "unit_price_cents": 12900,
        "line_total_cents": 25800
      }
    ]
  },
  "reserved_sku_id": "rr-mist-41",
  "available_quantity": 1
}
```

The same key and same request return the persisted original status/body with `Idempotency-Replayed: true`. Reusing a key for a different request returns `409 IDEMPOTENCY_KEY_REUSED`.

Other expected errors are structured as follows:

```json
{"error":{"code":"OUT_OF_STOCK","message":"The selected quantity is no longer available."}}
```

| Status | Error code | Meaning |
| --- | --- | --- |
| 404 | `SKU_NOT_FOUND` | SKU does not exist |
| 409 | `OUT_OF_STOCK` | The atomic reservation could not obtain enough available stock |
| 409 | `IDEMPOTENCY_KEY_REUSED` | A key was used with a different request body |
| 422 | `VALIDATION_ERROR` | Missing/invalid request data |

### `GET /api/cart`

Returns the seeded anonymous `demo-cart` and its quantity total. Authentication is intentionally outside this assessment's scope.

## Architecture and key decisions

```text
React UI → typed API client → FastAPI route → cart service → SQLite
                                      │              ├─ idempotency record
                                      │              ├─ conditional SKU update
                                      │              └─ cart item write
                                      └─ structured JSON response
```

### Inventory and concurrent requests

Adding to the cart creates an inventory reservation. It does not decrement `on_hand`; it atomically increments `reserved` only when:

```sql
on_hand - reserved >= requested_quantity
```

The `UPDATE` performs both the check and mutation. Therefore two concurrent attempts for the final unit cannot both report success. The transaction also creates an idempotency record under a unique `(scope, key)` constraint before making the stock mutation. This is more reliable than a Python `Lock`, which would only protect one process.

The repository includes an integration test that launches two concurrent requests for one unit and asserts exactly one `201`, one `409`, and a final reservation of one.

SQLite is chosen because the brief explicitly permits it and it gives a zero-configuration reviewer experience. The conditional update is safe across SQLite connections; a horizontally scaled production version would retain this design but use PostgreSQL and a reservation-expiry job.

### Frontend state

- The selected SKU is derived from options via a pure `resolveVariant` function; price, image and stock are never duplicated as mutable UI state.
- TanStack Query owns server data. A successful add invalidates both product and cart, reconciling any stock change from the server.
- One add attempt owns one generated idempotency key. A retry of an uncertain network request reuses that key, whereas changing SKU or quantity starts a new attempt.
- Native `fieldset`, `legend`, buttons, visible focus styles and an `aria-live` feedback region make the main flow keyboard and screen-reader usable.

### Scope intentionally excluded

The assignment explicitly excludes auth, checkout and payments. The cart is therefore one seeded anonymous cart. Reservations also have no TTL release endpoint; a real checkout would add `reservation_expires_at`, release/confirm transitions and a cleanup worker. These limits are documented rather than hidden.

## Algorithm notes

### Task A

`InventoryLedger` processes each command once with hash sets/maps for processed event IDs and open order reservations. It validates before mutation and records a syntactically addressable rejected event as processed, so retries are deterministic.

The parser enforces the assignment limits (`0 <= S <= 10^12`, `1 <= N <= 200,000`, and `1 <= qty <= 10^12`) and requires event/order IDs to be printable ASCII tokens. Task B similarly enforces `W <= 30`, `Q <= 2,000`, `stock <= 2,000`, and cost values up to `10^6` before running the optimizer.

- Time: **O(N)**
- Space: **O(E + O)** for processed event IDs and open orders

### Task B

The optimiser first derives the minimum possible warehouse count from capacities. It then runs an exact bounded-knapsack dynamic program for exactly that count and requested quantity. A monotonic queue optimises each warehouse's linear shipping-cost transition; a suffix-cost reconstruction chooses the first viable warehouse ID and then its smallest viable allocation, which implements the final lexicographic tie-break.

- Time: **O(W × K × Q)**, where `K` is the minimum number of warehouses
- Space: **O(W × K × Q)** for suffix costs retained to reconstruct the lexicographically smallest plan

## Reuse and attribution

No application source file was copied from an external repository. The project independently implements the domain logic, API, UI and tests. The following sources informed narrow engineering choices and are linked here so they can be inspected:

- [FastAPI full-stack template](https://github.com/fastapi/full-stack-fastapi-template): typed frontend/backend boundaries and testable frontend structure.
- [Quartermaster](https://github.com/JumpMasters/quartermaster): inventory invariants and concurrency-test ideas.
- [Allo](https://github.com/Dekshith14/allo): atomic conditional reservation and idempotent-response pattern.

`C/answers.md` cites current official Xero documentation separately.

## AI assistance disclosure

AI assistance was used for initial scaffolding, code drafting, test outline generation, documentation drafting and iterative verification. Before submitting this assessment, the candidate should review this statement for accuracy, understand every design decision, and be prepared to change/debug the implementation live. No credentials, customer data or external service keys are included.
