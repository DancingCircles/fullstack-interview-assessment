from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from pdp_api.db.models import Base, Product, Sku


class Database:
    def __init__(self, url: str) -> None:
        self.engine = create_engine(
            url,
            connect_args={"check_same_thread": False, "timeout": 10},
            future=True,
        )
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)

    def session(self) -> Generator[Session, None, None]:
        with self.session_factory() as session:
            yield session

    def initialise(self) -> None:
        Base.metadata.create_all(self.engine)
        with self.session_factory.begin() as session:
            if session.scalar(select(Product.id).limit(1)) is None:
                _seed(session)

    def dispose(self) -> None:
        self.engine.dispose()


def _seed(session: Session) -> None:
    session.add(
        Product(
            id="ridge-runner",
            name="Ridge Runner",
            description="A lightweight trail shoe with stable cushioning for everyday miles.",
        )
    )
    session.add_all(
        [
            Sku(id="rr-mist-40", product_id="ridge-runner", color="Mist", size="40", price_cents=12900, on_hand=8, reserved=0, image_url="/products/mist.png"),
            Sku(id="rr-mist-41", product_id="ridge-runner", color="Mist", size="41", price_cents=12900, on_hand=3, reserved=0, image_url="/products/mist.png"),
            Sku(id="rr-mist-42", product_id="ridge-runner", color="Mist", size="42", price_cents=12900, on_hand=0, reserved=0, image_url="/products/mist.png"),
            Sku(id="rr-graphite-40", product_id="ridge-runner", color="Graphite", size="40", price_cents=13900, on_hand=4, reserved=0, image_url="/products/graphite.png"),
            Sku(id="rr-graphite-41", product_id="ridge-runner", color="Graphite", size="41", price_cents=13900, reserved=0, on_hand=6, image_url="/products/graphite.png"),
            Sku(id="rr-clay-41", product_id="ridge-runner", color="Clay", size="41", price_cents=13400, on_hand=2, reserved=0, image_url="/products/clay.png"),
        ]
    )
