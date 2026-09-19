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
    items = sorted(warehouses, key=lambda warehouse: warehouse.warehouse_id)
    _validate(items, demand)
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
    if demand < 1:
        raise ValueError("Demand must be positive")
    ids = [item.warehouse_id for item in items]
    if len(ids) != len(set(ids)):
        raise ValueError("Warehouse ids must be unique")
    for item in items:
        if not item.warehouse_id or min(item.stock, item.fixed_cost, item.unit_cost) < 0:
            raise ValueError("Warehouse values must be non-negative and ids non-empty")


def parse_input(lines: Iterable[str]) -> tuple[list[Warehouse], int]:
    iterator = iter(lines)
    try:
        warehouse_count, demand = map(int, next(iterator).split())
    except (StopIteration, ValueError):
        raise ValueError("Expected header: warehouse_count demand") from None

    warehouses: list[Warehouse] = []
    for _ in range(warehouse_count):
        try:
            warehouse_id, stock, fixed_cost, unit_cost = next(iterator).split()
            warehouses.append(Warehouse(warehouse_id, int(stock), int(fixed_cost), int(unit_cost)))
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

