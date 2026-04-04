

from __future__ import annotations

import argparse
import os
import sys
from decimal import Decimal
from typing import Optional


try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  

from bot.client import BinanceFuturesClient, BinanceAPIError, BinanceNetworkError
from bot.logging_config import setup_logging
from bot.orders import OrderResult, place_order
from bot.validators import validate_all


setup_logging()

import logging
logger = logging.getLogger(__name__)




DIVIDER = "─" * 54


def _print_request_summary(
    symbol: str,
    side: str,
    order_type: str,
    quantity: Decimal,
    price: Optional[Decimal],
    stop_price: Optional[Decimal],
) -> None:
    print(f"\n{DIVIDER}")
    print("  📋  ORDER REQUEST SUMMARY")
    print(DIVIDER)
    print(f"  Symbol    : {symbol}")
    print(f"  Side      : {side}")
    print(f"  Type      : {order_type}")
    print(f"  Quantity  : {quantity}")
    if price is not None:
        print(f"  Price     : {price}")
    if stop_price is not None:
        print(f"  Stop Price: {stop_price}")
    print(DIVIDER)


def _print_order_result(result: OrderResult) -> None:
    print(f"\n{DIVIDER}")
    print("  ✅  ORDER PLACED SUCCESSFULLY")
    print(DIVIDER)
    print(f"  Order ID       : {result.order_id}")
    print(f"  Client Order ID: {result.client_order_id}")
    print(f"  Status         : {result.status}")
    print(f"  Symbol         : {result.symbol}")
    print(f"  Side           : {result.side}")
    print(f"  Type           : {result.order_type}")
    print(f"  Orig Qty       : {result.orig_qty}")
    print(f"  Executed Qty   : {result.executed_qty}")
    if result.avg_price and result.avg_price != "0":
        print(f"  Avg Price      : {result.avg_price}")
    if result.price and result.price != "0":
        print(f"  Limit Price    : {result.price}")
    print(DIVIDER)


def _print_error(msg: str) -> None:
    print(f"\n{DIVIDER}")
    print("  ❌  ERROR")
    print(DIVIDER)
    print(f"  {msg}")
    print(DIVIDER)




def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading-bot",
        description="Binance Futures Testnet — place MARKET / LIMIT / STOP_LIMIT orders",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Examples:
  MARKET BUY:
    python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

  LIMIT SELL:
    python cli.py --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.1 --price 3000

  STOP-LIMIT BUY:
    python cli.py --symbol BTCUSDT --side BUY --type STOP_LIMIT \\
                  --quantity 0.001 --price 68000 --stop-price 67500
""",
    )


    order_group = parser.add_argument_group("Order parameters")
    order_group.add_argument(
        "--symbol", "-s",
        required=True,
        help="Trading pair symbol, e.g. BTCUSDT",
    )
    order_group.add_argument(
        "--side",
        required=True,
        choices=["BUY", "SELL", "buy", "sell"],
        help="Order direction: BUY or SELL",
    )
    order_group.add_argument(
        "--type", "-t",
        dest="order_type",
        required=True,
        choices=["MARKET", "LIMIT", "STOP_LIMIT", "market", "limit", "stop_limit"],
        help="Order type: MARKET, LIMIT, or STOP_LIMIT",
    )
    order_group.add_argument(
        "--quantity", "-q",
        required=True,
        help="Order quantity (number of contracts/coins)",
    )
    order_group.add_argument(
        "--price", "-p",
        default=None,
        help="Limit price (required for LIMIT and STOP_LIMIT)",
    )
    order_group.add_argument(
        "--stop-price",
        default=None,
        dest="stop_price",
        help="Stop trigger price (required for STOP_LIMIT)",
    )

    # ── Authentication ─────────────────────────────────────────────────────
    auth_group = parser.add_argument_group(
        "Authentication (overrides env vars BINANCE_API_KEY / BINANCE_API_SECRET)"
    )
    auth_group.add_argument("--api-key",    default=None, help="Binance Futures Testnet API key")
    auth_group.add_argument("--api-secret", default=None, help="Binance Futures Testnet API secret")

    return parser




def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

   
    api_key    = args.api_key    or os.getenv("BINANCE_API_KEY",    "")
    api_secret = args.api_secret or os.getenv("BINANCE_API_SECRET", "")

    if not api_key or not api_secret:
        _print_error(
            "API key / secret not found.\n"
            "  Set BINANCE_API_KEY and BINANCE_API_SECRET environment variables,\n"
            "  or pass --api-key / --api-secret on the command line."
        )
        logger.error("Missing API credentials — aborting.")
        sys.exit(1)

    
    try:
        validated = validate_all(
            symbol=args.symbol,
            side=args.side,
            order_type=args.order_type,
            quantity=args.quantity,
            price=args.price,
            stop_price=args.stop_price,
        )
    except ValueError as exc:
        _print_error(f"Validation error: {exc}")
        logger.error("Validation failed: %s", exc)
        sys.exit(1)

    
    _print_request_summary(
        symbol=validated["symbol"],
        side=validated["side"],
        order_type=validated["order_type"],
        quantity=validated["quantity"],
        price=validated["price"],
        stop_price=validated["stop_price"],
    )

   
    try:
        with BinanceFuturesClient(api_key=api_key, api_secret=api_secret) as client:
            result = place_order(
                client=client,
                symbol=validated["symbol"],
                side=validated["side"],
                order_type=validated["order_type"],
                quantity=validated["quantity"],
                price=validated["price"],
                stop_price=validated["stop_price"],
            )
        _print_order_result(result)

    except BinanceAPIError as exc:
        _print_error(f"Binance API error [{exc.code}]: {exc.message}")
        logger.error("BinanceAPIError: code=%s msg=%s", exc.code, exc.message)
        sys.exit(1)

    except BinanceNetworkError as exc:
        _print_error(f"Network error: {exc}\nCheck your internet connection and try again.")
        logger.error("BinanceNetworkError: %s", exc)
        sys.exit(1)

    except Exception as exc:
        _print_error(f"Unexpected error: {exc}")
        logger.exception("Unexpected error during order placement")
        sys.exit(1)


if __name__ == "__main__":
    main()
