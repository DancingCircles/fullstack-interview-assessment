from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from pdp_api.api.routes import router
from pdp_api.db.database import Database


def create_app(database_url: str = "sqlite:///./data/pdp.db") -> FastAPI:
    database = Database(database_url)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        database.initialise()
        yield
        database.dispose()

    app = FastAPI(title="Ridge Runner PDP API", version="1.0.0", lifespan=lifespan)
    app.state.database = database
    app.include_router(router)
    static_products = Path(__file__).resolve().parent.parent / "static" / "products"
    app.mount("/products", StaticFiles(directory=static_products), name="products")

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed.",
                    "fields": exc.errors(),
                }
            },
        )

    @app.exception_handler(HTTPException)
    async def http_error(_: Request, exc: HTTPException) -> JSONResponse:
        code = "NOT_FOUND" if exc.status_code == 404 else "REQUEST_FAILED"
        message = str(exc.detail) if isinstance(exc.detail, str) else "The request could not be completed."
        return JSONResponse(status_code=exc.status_code, content={"error": {"code": code, "message": message}})

    @app.exception_handler(Exception)
    async def unexpected_error(_: Request, __: Exception) -> JSONResponse:
        # Keep internal details out of the API response while preserving the
        # same error contract as expected validation and business failures.
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "INTERNAL_SERVER_ERROR", "message": "An unexpected error occurred."}},
        )

    return app


app = create_app()
