from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, Optional

from .client import BinanceFuturesClient

logger = logging.getLogger(__name__)

ORDER_ENDPOINT = "/fapi/v1/order"




@dataclass
class OrderResult:
    """Normalised representation of a Binance order response."""

    order_id: int
    symbol: str
    status: str
    side: str
    order_type: str
    orig_qty: str
    executed_qty: str
    avg_price: str
    price: str 
    client_order_id: str
    raw: Dict[str, Any] = field(repr=False, default_factory=dict)

    @classmethod
    def from_response(cls, data: Dict[str, Any]) -> "OrderResult":
        return cls(
            order_id=data.get("orderId", 0),
            symbol=data.get("symbol", ""),
            status=data.get("status", ""),
            side=data.get("side", ""),
            order_type=data.get("type", ""),
            orig_qty=data.get("origQty", "0"),
            executed_qty=data.get("executedQty", "0"),
            avg_price=data.get("avgPrice", "0"),
            price=data.get("price", "0"),
            client_order_id=data.get("clientOrderId", ""),
            raw=data,
        )




def _build_base_params(symbol: str, side: str, order_type: str, quantity: Decimal) -> Dict[str, Any]:
    """Return the parameter dict fields common to every order type."""
    return {
        "symbol":   symbol,
        "side":     side,
        "type":     order_type,
        "quantity": str(quantity),
    }


def _place_order(client: BinanceFuturesClient, params: Dict[str, Any]) -> OrderResult:
    """Send the order to Binance and parse the result."""
    logger.info("Placing order — params=%s", {k: v for k, v in params.items()})
    response = client.post(ORDER_ENDPOINT, params)
    logger.info("Order response — %s", response)
    result = OrderResult.from_response(response)
    logger.info(
        "Order placed successfully — orderId=%s status=%s",
        result.order_id, result.status,
    )
    return result



def place_market_order(
    client: BinanceFuturesClient,
    symbol: str,
    side: str,
    quantity: Decimal,
) -> OrderResult:
    """
    Place a MARKET order.

    Args:
        client:   Authenticated BinanceFuturesClient instance.
        symbol:   Trading pair, e.g. "BTCUSDT".
        side:     "BUY" or "SELL".
        quantity: Number of contracts / coins.

    Returns:
        OrderResult with server-assigned orderId, status, executedQty, avgPrice.
    """
    params = _build_base_params(symbol, side, "MARKET", quantity)
  
    return _place_order(client, params)


def place_limit_order(
    client: BinanceFuturesClient,
    symbol: str,
    side: str,
    quantity: Decimal,
    price: Decimal,
    time_in_force: str = "GTC",
) -> OrderResult:
    """
    Place a LIMIT order.

    Args:
        client:        Authenticated BinanceFuturesClient instance.
        symbol:        Trading pair, e.g. "BTCUSDT".
        side:          "BUY" or "SELL".
        quantity:      Number of contracts / coins.
        price:         Limit price.
        time_in_force: "GTC" (default) | "IOC" | "FOK".

    Returns:
        OrderResult with order details.
    """
    params = _build_base_params(symbol, side, "LIMIT", quantity)
    params["price"] = str(price)
    params["timeInForce"] = time_in_force
    return _place_order(client, params)


def place_stop_limit_order(
    client: BinanceFuturesClient,
    symbol: str,
    side: str,
    quantity: Decimal,
    price: Decimal,
    stop_price: Decimal,
    time_in_force: str = "GTC",
) -> OrderResult:
    """
    BONUS: Place a STOP_MARKET / STOP order (stop-limit on Binance Futures).

    Binance Futures uses `type=STOP` for stop-limit orders.

    Args:
        client:     Authenticated BinanceFuturesClient instance.
        symbol:     Trading pair, e.g. "BTCUSDT".
        side:       "BUY" or "SELL".
        quantity:   Number of contracts / coins.
        price:      Limit price to execute at once stop is triggered.
        stop_price: Price that triggers the order.

    Returns:
        OrderResult with order details.
    """
    params = _build_base_params(symbol, side, "STOP", quantity)
    params["price"] = str(price)
    params["stopPrice"] = str(stop_price)
    params["timeInForce"] = time_in_force
    return _place_order(client, params)



def place_order(
    client: BinanceFuturesClient,
    symbol: str,
    side: str,
    order_type: str,
    quantity: Decimal,
    price: Optional[Decimal] = None,
    stop_price: Optional[Decimal] = None,
) -> OrderResult:
    """
    Unified dispatcher — routes to the correct order function based on *order_type*.

    Args:
        client:     Authenticated BinanceFuturesClient.
        symbol:     e.g. "BTCUSDT"
        side:       "BUY" | "SELL"
        order_type: "MARKET" | "LIMIT" | "STOP_LIMIT"
        quantity:   Positive Decimal
        price:      Required for LIMIT / STOP_LIMIT
        stop_price: Required for STOP_LIMIT

    Returns:
        OrderResult
    """
    if order_type == "MARKET":
        return place_market_order(client, symbol, side, quantity)

    elif order_type == "LIMIT":
        if price is None:
            raise ValueError("Price must be provided for LIMIT orders.")
        return place_limit_order(client, symbol, side, quantity, price)

    elif order_type == "STOP_LIMIT":
        if price is None or stop_price is None:
            raise ValueError("Both --price and --stop-price are required for STOP_LIMIT orders.")
        return place_stop_limit_order(client, symbol, side, quantity, price, stop_price)

    else:
        raise ValueError(f"Unsupported order type: {order_type!r}")
