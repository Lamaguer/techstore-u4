from decimal import Decimal

import pytest

from app.domain import (
    InvalidOrderData,
    InvalidOrderTransition,
    Money,
    OrderItem,
    OrderItemLimitExceeded,
    OrderStatus,
)
from app.specifications import discount_rate_for
from cargar_csv import load_fixture


def event_names(order):
    return [event.name for event in order.events]


def test_money_rejects_negative_amount():
    with pytest.raises(InvalidOrderData):
        Money(Decimal("-1"))


def test_o001_starts_with_expected_fixture_data():
    orders = load_fixture()
    order = orders["O001"]

    assert order.status == OrderStatus.DRAFT
    assert order.units == 4
    assert order.total.amount == Decimal("2100.00")


def test_e01_o001_vip_order_receives_ten_percent_discount():
    order = load_fixture()["O001"]

    assert order.status == OrderStatus.DRAFT
    assert discount_rate_for(order) == Decimal("0.10")
    assert event_names(order) == []


def test_e02_o002_non_vip_order_receives_no_discount():
    order = load_fixture()["O002"]

    assert order.status == OrderStatus.DRAFT
    assert discount_rate_for(order) == Decimal("0")
    assert event_names(order) == []


def test_e03_o003_inactive_customer_cannot_confirm():
    order = load_fixture()["O003"]

    with pytest.raises(InvalidOrderData):
        order.confirm()

    assert order.status == OrderStatus.DRAFT
    assert event_names(order) == []


def test_e04_o005_active_promotion_blocks_discount():
    order = load_fixture()["O005"]

    assert order.status == OrderStatus.DRAFT
    assert discount_rate_for(order) == Decimal("0")
    assert event_names(order) == []


def test_e05_o006_order_receives_five_percent_discount():
    order = load_fixture()["O006"]

    assert order.status == OrderStatus.DRAFT
    assert discount_rate_for(order) == Decimal("0.05")
    assert event_names(order) == []


def test_e06_o007_empty_order_cannot_confirm():
    order = load_fixture()["O007"]

    with pytest.raises(InvalidOrderData):
        order.confirm()

    assert order.status == OrderStatus.DRAFT
    assert event_names(order) == []


def test_e07_o008_order_with_twenty_units_can_be_confirmed():
    order = load_fixture()["O008"]

    assert order.units == 20
    order.confirm()

    assert order.status == OrderStatus.CONFIRMED
    assert event_names(order) == ["OrderConfirmed"]


def test_e08_o009_adding_two_units_would_exceed_the_limit():
    order = load_fixture()["O009"]
    item = OrderItem("SKU003", 2, Money(Decimal("120.00")))

    with pytest.raises(OrderItemLimitExceeded):
        order.add_item(item)

    assert order.status == OrderStatus.DRAFT
    assert order.units == 19
    assert event_names(order) == []


def test_e09_o010_exactly_five_hundred_does_not_qualify_for_discount():
    order = load_fixture()["O010"]

    assert order.total.amount == Decimal("500.00")
    assert discount_rate_for(order) == Decimal("0")
    assert event_names(order) == []


def test_e10_o011_three_units_do_not_qualify_for_vip_discount():
    order = load_fixture()["O011"]

    assert order.units == 3
    assert discount_rate_for(order) == Decimal("0")
    assert event_names(order) == []


def test_e11_o012_cannot_ship_without_tracking_number():
    order = load_fixture()["O012"]
    order.confirm()

    with pytest.raises(InvalidOrderData):
        order.ship("")

    assert order.status == OrderStatus.CONFIRMED
    assert event_names(order) == ["OrderConfirmed"]


def test_e12_o013_second_confirmation_fails_without_another_event():
    order = load_fixture()["O013"]

    order.confirm()
    assert order.status == OrderStatus.CONFIRMED
    assert event_names(order) == ["OrderConfirmed"]

    with pytest.raises(InvalidOrderTransition):
        order.confirm()

    assert order.status == OrderStatus.CONFIRMED
    assert event_names(order) == ["OrderConfirmed"]


def test_e13_o014_shipped_order_cannot_be_cancelled():
    order = load_fixture()["O014"]
    order.confirm()
    order.ship("TRACK-O014")

    with pytest.raises(InvalidOrderTransition):
        order.cancel("Customer requested cancellation")

    assert order.status == OrderStatus.SHIPPED
    assert event_names(order) == ["OrderConfirmed", "OrderShipped"]


def test_e14_o015_shipped_order_can_be_returned():
    order = load_fixture()["O015"]
    order.confirm()
    order.ship("TRACK-O015")
    order.return_order()

    assert order.status == OrderStatus.RETURNED
    assert event_names(order) == [
        "OrderConfirmed",
        "OrderShipped",
        "OrderReturned",
    ]


def test_e15_o016_shipped_order_can_be_delivered():
    order = load_fixture()["O016"]
    order.confirm()
    order.ship("TRACK-O016")
    order.deliver()

    assert order.status == OrderStatus.DELIVERED
    assert event_names(order) == [
        "OrderConfirmed",
        "OrderShipped",
        "OrderDelivered",
    ]
