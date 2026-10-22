from collections.abc import Callable

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.domain import InvalidOrderData, InvalidOrderTransition, Order
from cargar_csv import load_fixture


class ShipOrderRequest(BaseModel):
    tracking_number: str


class CancelOrderRequest(BaseModel):
    reason: str


app = FastAPI(title="TechStore U4")
orders = load_fixture()


def _find_order(order_id: str) -> Order:
    order = orders.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="No existe el pedido")
    return order


def _serialize_order(order: Order) -> dict:
    return {
        "id": order.id,
        "status": order.status.value,
        "customer": {
            "id": order.customer.id,
            "is_vip": order.customer.is_vip,
            "active": order.customer.active,
        },
        "has_promotion": order.has_promotion,
        "items": [
            {
                "sku": item.sku,
                "quantity": item.quantity,
                "unit_price": {
                    "amount": str(item.unit_price.amount),
                    "currency": item.unit_price.currency,
                },
            }
            for item in order.items
        ],
        "units": order.units,
        "total": {
            "amount": str(order.total.amount),
            "currency": order.total.currency,
        },
        "events": [
            {
                "name": event.name,
                "order_id": event.order_id,
                "occurred_at": event.occurred_at.isoformat(),
            }
            for event in order.events
        ],
    }


def _run_order_action(order: Order, action: Callable[[], None]) -> dict:
    try:
        action()
    except InvalidOrderTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except InvalidOrderData as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _serialize_order(order)


@app.get("/orders/{order_id}") #Devuelve datos del pedido, estado, articulos y eventos.
def get_order(order_id: str):
    return _serialize_order(_find_order(order_id))


@app.post("/orders/{order_id}/confirm") #Conserva la informacion existente
def confirm_order(order_id: str):
    order = _find_order(order_id)
    return _run_order_action(order, order.confirm)


@app.post("/orders/{order_id}/ship") #Recibe el tracking number
def ship_order(order_id: str, request: ShipOrderRequest):
    order = _find_order(order_id)
    return _run_order_action(
        order, lambda: order.ship(request.tracking_number)
    )


@app.post("/orders/{order_id}/cancel") #Recibe razon
def cancel_order(order_id: str, request: CancelOrderRequest):
    order = _find_order(order_id)
    return _run_order_action(order, lambda: order.cancel(request.reason))
