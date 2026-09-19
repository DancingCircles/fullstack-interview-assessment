"""A deterministic, idempotent command processor for one SKU."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

MAX_STOCK = 10**12
MAX_COMMANDS = 200_000
MAX_QUANTITY = 10**12

@dataclass
class InventoryLedger:
    on_hand: int
    reserved: int = 0
    reservations: dict[str, int] = field(default_factory=dict)
    processed_event_ids: set[str] = field(default_factory=set)

    @property
    def available(self) -> int:
        return self.on_hand - self.reserved

    def process(self, raw_command: str) -> str:
        """Apply one command atomically and return its outcome.

        A syntactically addressable event (a non-empty second token) is recorded
        even when rejected. A line without an event id cannot be replayed and is
        simply rejected.
        """
        parts = raw_command.split()
        event_id = parts[1] if len(parts) >= 2 and parts[1] else None
        if event_id and event_id in self.processed_event_ids:
            return "DUPLICATE"

        outcome = self._validate_and_apply(parts)
        if event_id:
            self.processed_event_ids.add(event_id)
        return outcome

    def _validate_and_apply(self, parts: list[str]) -> str:
        if not parts:
            return "REJECTED"

        command = parts[0]
        if command == "RESTOCK":
            if len(parts) != 3 or not _ascii_token(parts[1]):
                return "REJECTED"
            qty = _positive_int(parts[2])
            if qty is None:
                return "REJECTED"
            self.on_hand += qty
            return "OK"

        if command not in {"RESERVE", "RELEASE", "SHIP"} or len(parts) != 4:
            return "REJECTED"

        _, _, order_id, raw_qty = parts
        qty = _positive_int(raw_qty)
        if not _ascii_token(parts[1]) or not _ascii_token(order_id) or qty is None:
            return "REJECTED"

        current_reservation = self.reservations.get(order_id, 0)
        if command == "RESERVE":
            if qty > self.available:
                return "REJECTED"
            self.reservations[order_id] = current_reservation + qty
            self.reserved += qty
            return "OK"

        if qty > current_reservation:
            return "REJECTED"

        if command == "RELEASE":
            self._decrease_reservation(order_id, qty)
            self.reserved -= qty
            return "OK"

        # SHIP has passed the reservation guard, so both mutations are safe.
        self._decrease_reservation(order_id, qty)
        self.reserved -= qty
        self.on_hand -= qty
        return "OK"

    def _decrease_reservation(self, order_id: str, qty: int) -> None:
        remaining = self.reservations[order_id] - qty
        if remaining:
            self.reservations[order_id] = remaining
        else:
            del self.reservations[order_id]

    def snapshot(self, outcome: str) -> str:
        return f"{outcome} {self.on_hand} {self.reserved}"

    def open_reservations(self) -> list[tuple[str, int]]:
        return sorted(self.reservations.items())


def _ascii_token(value: str) -> bool:
    return bool(value) and all(0x21 <= ord(character) <= 0x7E for character in value)


def _positive_int(value: str, *, maximum: int = MAX_QUANTITY) -> int | None:
    if not value or not value.isascii() or not value.isdecimal():
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if 0 < parsed <= maximum else None


def _non_negative_int(value: str, *, maximum: int) -> int | None:
    if not value or not value.isascii() or not value.isdecimal():
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if parsed <= maximum else None


def process_input(lines: Iterable[str]) -> list[str]:
    iterator = iter(lines)
    try:
        header = next(iterator).split()
        if len(header) != 2:
            raise ValueError
        initial_stock = _non_negative_int(header[0], maximum=MAX_STOCK)
        command_count = _positive_int(header[1], maximum=MAX_COMMANDS)
        if initial_stock is None or command_count is None:
            raise ValueError
    except (StopIteration, ValueError):
        raise ValueError("Expected header: initial_stock command_count") from None

    ledger = InventoryLedger(on_hand=initial_stock)
    output: list[str] = []
    for _ in range(command_count):
        try:
            command = next(iterator)
        except StopIteration:
            command = ""
        outcome = ledger.process(command)
        output.append(ledger.snapshot(outcome))

    open_reservations = ledger.open_reservations()
    output.append(f"OPEN {len(open_reservations)}")
    output.extend(f"{order_id} {qty}" for order_id, qty in open_reservations)
    return output


def main() -> None:
    import sys

    sys.stdout.write("\n".join(process_input(sys.stdin)) + "\n")


if __name__ == "__main__":
    main()
