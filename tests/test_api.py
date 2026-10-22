import pytest
from fastapi.testclient import TestClient

from app import api
from app.domain import OrderStatus
from cargar_csv import load_fixture


@pytest.fixture(autouse=True)
def reset_orders(monkeypatch):
    monkeypatch.setattr(api, "orders", load_fixture())


@pytest.fixture
def client():
    return TestClient(api.app)


def test_get_order_returns_order_details(client):
    response = client.get("/orders/O001")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "O001"
    assert body["status"] == "DRAFT"
    assert body["units"] == 4
    assert body["total"]["amount"] == "2100.00"
    assert body["events"] == []


def test_get_unknown_order_returns_404(client):
    response = client.get("/orders/unknown")

    assert response.status_code == 404


def test_confirm_endpoint_calls_order_method(client):
    response = client.post("/orders/O013/confirm")

    assert response.status_code == 200
    assert response.json()["status"] == "CONFIRMED"
    assert [event["name"] for event in response.json()["events"]] == [
        "OrderConfirmed"
    ]


def test_invalid_confirmation_returns_422_without_event(client):
    response = client.post("/orders/O003/confirm")

    assert response.status_code == 422
    order = api.orders["O003"]
    assert order.status == OrderStatus.DRAFT
    assert order.events == []


def test_second_confirmation_returns_409_without_duplicate_event(client):
    assert client.post("/orders/O013/confirm").status_code == 200

    response = client.post("/orders/O013/confirm")

    assert response.status_code == 409
    order = api.orders["O013"]
    assert order.status == OrderStatus.CONFIRMED
    assert [event.name for event in order.events] == ["OrderConfirmed"]


def test_ship_endpoint_requires_tracking_number(client):
    assert client.post("/orders/O012/confirm").status_code == 200

    response = client.post(
        "/orders/O012/ship", json={"tracking_number": " "}
    )

    assert response.status_code == 422
    order = api.orders["O012"]
    assert order.status == OrderStatus.CONFIRMED
    assert [event.name for event in order.events] == ["OrderConfirmed"]


def test_ship_endpoint_updates_state_and_event(client):
    assert client.post("/orders/O012/confirm").status_code == 200

    response = client.post(
        "/orders/O012/ship", json={"tracking_number": "TRACK-012"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "SHIPPED"
    assert [event["name"] for event in response.json()["events"]] == [
        "OrderConfirmed",
        "OrderShipped",
    ]


def test_cancel_endpoint_updates_state_and_event(client):
    assert client.post("/orders/O013/confirm").status_code == 200

    response = client.post(
        "/orders/O013/cancel", json={"reason": "Customer request"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"
    assert [event["name"] for event in response.json()["events"]] == [
        "OrderConfirmed",
        "OrderCancelled",
    ]


def test_cancel_endpoint_requires_reason(client):
    assert client.post("/orders/O013/confirm").status_code == 200

    response = client.post("/orders/O013/cancel", json={"reason": ""})

    assert response.status_code == 422
    order = api.orders["O013"]
    assert order.status == OrderStatus.CONFIRMED
    assert [event.name for event in order.events] == ["OrderConfirmed"]


def test_cannot_cancel_shipped_order(client):
    assert client.post("/orders/O014/confirm").status_code == 200
    assert client.post(
        "/orders/O014/ship", json={"tracking_number": "TRACK-014"}
    ).status_code == 200

    response = client.post(
        "/orders/O014/cancel", json={"reason": "Too late"}
    )

    assert response.status_code == 409
    order = api.orders["O014"]
    assert order.status == OrderStatus.SHIPPED
    assert [event.name for event in order.events] == [
        "OrderConfirmed",
        "OrderShipped",
    ]