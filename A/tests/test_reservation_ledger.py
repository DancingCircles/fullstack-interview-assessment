from A.reservation_ledger import InventoryLedger, process_input


def test_prompt_example() -> None:
    result = process_input(
        [
            "10 6\n",
            "RESERVE e1 o100 4\n",
            "RESERVE e2 o200 7\n",
            "SHIP e3 o100 2\n",
            "RELEASE e4 o100 2\n",
            "RESTOCK e5 3\n",
            "RESERVE e2 o99 1\n",
        ]
    )

    assert result == [
        "OK 10 4",
        "REJECTED 10 4",
        "OK 8 2",
        "OK 8 0",
        "OK 11 0",
        "DUPLICATE 11 0",
        "OPEN 0",
    ]


def test_rejected_event_is_still_idempotent() -> None:
    ledger = InventoryLedger(on_hand=1)

    assert ledger.process("RESERVE e1 order-1 2") == "REJECTED"
    assert ledger.process("RESERVE e1 order-1 1") == "DUPLICATE"
    assert (ledger.on_hand, ledger.reserved, ledger.reservations) == (1, 0, {})


def test_invalid_command_does_not_partially_mutate_state() -> None:
    ledger = InventoryLedger(on_hand=3)
    assert ledger.process("RESERVE e1 order-1 nope") == "REJECTED"
    assert ledger.process("SHIP e2 order-1 1") == "REJECTED"
    assert (ledger.on_hand, ledger.reserved, ledger.reservations) == (3, 0, {})


def test_open_reservations_are_sorted_and_zero_entries_removed() -> None:
    result = process_input(
        [
            "10 4\n",
            "RESERVE e1 z-order 3\n",
            "RESERVE e2 a-order 2\n",
            "RELEASE e3 z-order 3\n",
            "SHIP e4 a-order 1\n",
        ]
    )
    assert result[-2:] == ["OPEN 1", "a-order 1"]

