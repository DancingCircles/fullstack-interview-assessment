from B.fulfillment_optimizer import Warehouse, optimize


def test_prompt_example_prefers_one_warehouse() -> None:
    plan = optimize(
        [
            Warehouse("AU", 5, 8, 2),
            Warehouse("CN", 7, 20, 1),
            Warehouse("US", 4, 3, 4),
        ],
        demand=7,
    )
    assert plan is not None
    assert (plan.warehouses_used, plan.total_cost, plan.allocations) == (1, 27, (("CN", 7),))


def test_returns_none_when_capacity_is_insufficient() -> None:
    assert optimize([Warehouse("A", 2, 1, 1), Warehouse("B", 1, 1, 1)], 4) is None


def test_zero_stock_warehouse_is_not_selected() -> None:
    plan = optimize([Warehouse("A", 0, 0, 0), Warehouse("B", 3, 5, 2)], 3)
    assert plan is not None
    assert plan.allocations == (("B", 3),)


def test_cost_breaks_tie_after_minimum_warehouse_count() -> None:
    plan = optimize([Warehouse("A", 5, 10, 4), Warehouse("B", 5, 2, 3)], 5)
    assert plan is not None
    assert plan.allocations == (("B", 5),)
    assert plan.total_cost == 17


def test_assignment_list_lexicographically_breaks_perfect_tie() -> None:
    plan = optimize([Warehouse("B", 5, 1, 1), Warehouse("A", 5, 1, 1)], 5)
    assert plan is not None
    assert plan.allocations == (("A", 5),)


def test_large_demand_uses_minimum_count_before_cost() -> None:
    plan = optimize(
        [Warehouse("A", 2000, 1_000_000, 1), Warehouse("B", 1000, 0, 0)], 2000
    )
    assert plan is not None
    assert plan.warehouses_used == 1
    assert plan.allocations == (("A", 2000),)

