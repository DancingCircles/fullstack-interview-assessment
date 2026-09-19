"""Exact optimiser for the warehouse split problem.

The cost DP is a bounded knapsack. Its linear per-unit cost lets each warehouse
transition be evaluated with a monotonic queue rather than iterating every
possible allocated quantity.
"""

from __future__ import annotations

from array import array
from collections import deque
from dataclasses import dataclass
from typing import Iterable

INF = 10**15
MAX_WAREHOUSES = 30
MAX_DEMAND = 2_000
MAX_STOCK = 2_000
MAX_COST = 10**6


@dataclass(frozen=True)
class Warehouse:
    warehouse_id: str
    stock: int
    fixed_cost: int
    unit_cost: int


@dataclass(frozen=True)
class AllocationPlan:
    warehouses_used: int
    total_cost: int
    allocations: tuple[tuple[str, int], ...]


def optimize(warehouses: Iterable[Warehouse], demand: int) -> AllocationPlan | None:
    """Return the plan ordered by count, cost, then output-list lexicography."""
    items = list(warehouses)
    _validate(items, demand)
    items.sort(key=lambda warehouse: warehouse.warehouse_id)
    if sum(item.stock for item in items) < demand:
        return None

    # The minimum count is independent of costs: take capacities in descending order.
    accumulated = 0
    minimum_count = 0
    for item in sorted(items, key=lambda warehouse: warehouse.stock, reverse=True):
        if accumulated >= demand:
            break
        accumulated += item.stock
        minimum_count += 1

    suffix = _build_suffix_costs(items, demand, minimum_count)
    total_cost = suffix[0][minimum_count][demand]
    if total_cost == INF:
        return None

    allocations = _reconstruct_lexicographically_smallest(
        items, suffix, demand, minimum_count, total_cost
    )
    return AllocationPlan(minimum_count, total_cost, tuple(allocations))


def _build_suffix_costs(
    items: list[Warehouse], demand: int, max_count: int
) -> list[list[array]]:
    terminal = [array("q", [INF]) * (demand + 1) for _ in range(max_count + 1)]
    terminal[0][0] = 0
    suffix: list[list[array]] = [terminal]

    for item in reversed(items):
        previous = suffix[-1]
        current = [array("q", previous[count]) for count in range(max_count + 1)]
        capacity = min(item.stock, demand)

        for used_count in range(1, max_count + 1):
            source = previous[used_count - 1]
            target = current[used_count]
            candidates: deque[int] = deque()

            for quantity in range(1, demand + 1):
                prior_quantity = quantity - 1
                if source[prior_quantity] != INF:
                    candidate_value = source[prior_quantity] - item.unit_cost * prior_quantity
                    while candidates:
                        tail = candidates[-1]
                        tail_value = source[tail] - item.unit_cost * tail
                        if tail_value < candidate_value:
                            break
                        candidates.pop()
                    candidates.append(prior_quantity)

                earliest_allowed = quantity - capacity
                while candidates and candidates[0] < earliest_allowed:
                    candidates.popleft()

                if candidates:
                    best_prior = candidates[0]
                    include_cost = (
                        source[best_prior]
                        + item.fixed_cost
                        + item.unit_cost * (quantity - best_prior)
                    )
                    if include_cost < target[quantity]:
                        target[quantity] = include_cost

        suffix.append(current)

    suffix.reverse()
    return suffix


def _reconstruct_lexicographically_smallest(
    items: list[Warehouse],
    suffix: list[list[array]],
    demand: int,
    warehouses_used: int,
    total_cost: int,
) -> list[tuple[str, int]]:
    allocations: list[tuple[str, int]] = []
    remaining_demand = demand
    remaining_count = warehouses_used
    remaining_cost = total_cost

    for index, item in enumerate(items):
        if remaining_count == 0:
            break

        selected_quantity: int | None = None
        # Including the earliest possible warehouse is lexicographically smaller
        # than skipping it. With that warehouse included, the smallest feasible
        # positive allocation is the next lexicographic tie-breaker.
        for quantity in range(1, min(item.stock, remaining_demand) + 1):
            rest_cost = suffix[index + 1][remaining_count - 1][remaining_demand - quantity]
            if rest_cost == INF:
                continue
            if item.fixed_cost + item.unit_cost * quantity + rest_cost == remaining_cost:
                selected_quantity = quantity
                break

        if selected_quantity is not None:
            allocations.append((item.warehouse_id, selected_quantity))
            remaining_demand -= selected_quantity
            remaining_count -= 1
            remaining_cost = suffix[index + 1][remaining_count][remaining_demand]
            continue

        assert suffix[index + 1][remaining_count][remaining_demand] == remaining_cost

    assert remaining_demand == 0 and remaining_count == 0
    return allocations


def _validate(items: list[Warehouse], demand: int) -> None:
    if not 1 <= len(items) <= MAX_WAREHOUSES:
        raise ValueError(f"Warehouse count must be between 1 and {MAX_WAREHOUSES}")
    if not isinstance(demand, int) or isinstance(demand, bool) or not 1 <= demand <= MAX_DEMAND:
        raise ValueError(f"Demand must be between 1 and {MAX_DEMAND}")
    ids = [item.warehouse_id for item in items]
    if any(not isinstance(warehouse_id, str) or not _ascii_token(warehouse_id) for warehouse_id in ids):
        raise ValueError("Warehouse ids must be non-empty printable ASCII tokens")
    if len(ids) != len(set(ids)):
        raise ValueError("Warehouse ids must be unique")
    for item in items:
        if not _bounded_int(item.stock, maximum=MAX_STOCK):
            raise ValueError(f"Stock must be between 0 and {MAX_STOCK}")
        if not _bounded_int(item.fixed_cost, maximum=MAX_COST) or not _bounded_int(
            item.unit_cost, maximum=MAX_COST
        ):
            raise ValueError(f"Costs must be between 0 and {MAX_COST}")


def _ascii_token(value: str) -> bool:
    return bool(value) and all(0x21 <= ord(character) <= 0x7E for character in value)


def _bounded_int(value: object, *, maximum: int) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= maximum


def _parse_int_token(value: str, *, minimum: int, maximum: int) -> int:
    if not value or not value.isascii() or not value.isdecimal():
        raise ValueError
    parsed = int(value)
    if not minimum <= parsed <= maximum:
        raise ValueError
    return parsed


def parse_input(lines: Iterable[str]) -> tuple[list[Warehouse], int]:
    iterator = iter(lines)
    try:
        header = next(iterator).split()
        if len(header) != 2:
            raise ValueError
        warehouse_count = _parse_int_token(header[0], minimum=1, maximum=MAX_WAREHOUSES)
        demand = _parse_int_token(header[1], minimum=1, maximum=MAX_DEMAND)
    except (StopIteration, ValueError):
        raise ValueError("Expected header: warehouse_count demand") from None

    warehouses: list[Warehouse] = []
    for _ in range(warehouse_count):
        try:
            parts = next(iterator).split()
            if len(parts) != 4:
                raise ValueError
            warehouse_id, raw_stock, raw_fixed_cost, raw_unit_cost = parts
            if not _ascii_token(warehouse_id):
                raise ValueError
            warehouses.append(
                Warehouse(
                    warehouse_id,
                    _parse_int_token(raw_stock, minimum=0, maximum=MAX_STOCK),
                    _parse_int_token(raw_fixed_cost, minimum=0, maximum=MAX_COST),
                    _parse_int_token(raw_unit_cost, minimum=0, maximum=MAX_COST),
                )
            )
        except (StopIteration, ValueError):
            raise ValueError("Expected: warehouse_id stock fixed_cost unit_cost") from None
    return warehouses, demand


def render(plan: AllocationPlan | None) -> list[str]:
    if plan is None:
        return ["-1"]
    return [f"{plan.warehouses_used} {plan.total_cost}", *(f"{name} {qty}" for name, qty in plan.allocations)]


def main() -> None:
    import sys

    warehouses, demand = parse_input(sys.stdin)
    sys.stdout.write("\n".join(render(optimize(warehouses, demand))) + "\n")


if __name__ == "__main__":
    main()
