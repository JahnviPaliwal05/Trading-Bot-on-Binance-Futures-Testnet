

from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from typing import Optional

logger = logging.getLogger(__name__)



VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_LIMIT"}




def _to_decimal(value: str | float, label: str) -> Decimal:
    """Convert *value* to Decimal or raise a descriptive ValueError."""
    try:
        d = Decimal(str(value))
    except InvalidOperation:
        raise ValueError(f"{label} must be a valid number, got: {value!r}")
    return d




def validate_symbol(symbol: str) -> str:
    """
    Ensure the symbol is a non-empty uppercase alphanumeric string.
    Binance symbols are like BTCUSDT, ETHUSDT, etc.
    """
    if not symbol:
        raise ValueError("Symbol cannot be empty.")
    cleaned = symbol.strip().upper()
    if not cleaned.isalnum():
        raise ValueError(
            f"Symbol must be alphanumeric (e.g. BTCUSDT), got: {symbol!r}"
        )
    logger.debug("Symbol validated: %s", cleaned)
    return cleaned


def validate_side(side: str) -> str:
    """Ensure side is BUY or SELL (case-insensitive)."""
    upper = side.strip().upper()
    if upper not in VALID_SIDES:
        raise ValueError(
            f"Side must be one of {sorted(VALID_SIDES)}, got: {side!r}"
        )
    logger.debug("Side validated: %s", upper)
    return upper


def validate_order_type(order_type: str) -> str:
    """Ensure order_type is one of the supported types."""
    upper = order_type.strip().upper()
    if upper not in VALID_ORDER_TYPES:
        raise ValueError(
            f"Order type must be one of {sorted(VALID_ORDER_TYPES)}, got: {order_type!r}"
        )
    logger.debug("Order type validated: %s", upper)
    return upper


def validate_quantity(quantity: str | float) -> Decimal:
    """Quantity must be a positive number."""
    qty = _to_decimal(quantity, "Quantity")
    if qty <= 0:
        raise ValueError(f"Quantity must be positive, got: {quantity}")
    logger.debug("Quantity validated: %s", qty)
    return qty


def validate_price(price: str | float | None, order_type: str) -> Optional[Decimal]:
    """
    Price is required for LIMIT and STOP_LIMIT orders, forbidden for MARKET.
    Returns a Decimal when provided, None otherwise.
    """
    if order_type in {"LIMIT", "STOP_LIMIT"}:
        if price is None:
            raise ValueError(f"Price is required for {order_type} orders.")
        p = _to_decimal(price, "Price")
        if p <= 0:
            raise ValueError(f"Price must be positive, got: {price}")
        logger.debug("Price validated: %s", p)
        return p
    else:
        if price is not None:
            logger.warning(
                "Price (%s) supplied for MARKET order — it will be ignored.", price
            )
        return None


def validate_stop_price(stop_price: str | float | None, order_type: str) -> Optional[Decimal]:
    """
    Stop price is required specifically for STOP_LIMIT orders.
    """
    if order_type == "STOP_LIMIT":
        if stop_price is None:
            raise ValueError("Stop price (--stop-price) is required for STOP_LIMIT orders.")
        sp = _to_decimal(stop_price, "Stop price")
        if sp <= 0:
            raise ValueError(f"Stop price must be positive, got: {stop_price}")
        logger.debug("Stop price validated: %s", sp)
        return sp
    return None


def validate_all(
    symbol: str,
    side: str,
    order_type: str,
    quantity: str | float,
    price: str | float | None = None,
    stop_price: str | float | None = None,
) -> dict:
    """
    Run all validators in sequence and return a clean params dict.
    Raises ValueError with a descriptive message on the first failure.
    """
    params = {
        "symbol":      validate_symbol(symbol),
        "side":        validate_side(side),
        "order_type":  validate_order_type(order_type),
        "quantity":    validate_quantity(quantity),
        "price":       validate_price(price, order_type.strip().upper()),
        "stop_price":  validate_stop_price(stop_price, order_type.strip().upper()),
    }
    logger.info("All inputs validated: %s", params)
    return params
