# 🤖 Binance Futures Trading Bot (Testnet)

A clean, production-quality Python CLI for placing **MARKET**, **LIMIT**, and **STOP_LIMIT** orders on the **Binance USDT-M Futures Testnet**.

---

## 📁 Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py          # Package marker
│   ├── client.py            # Authenticated REST client (retry logic included)
│   ├── orders.py            # Order placement business logic
│   ├── validators.py        # Input validation helpers
│   └── logging_config.py    # File + console logging setup
├── cli.py                   # CLI entry point (argparse)
├── requirements.txt
└── README.md
```

---

## ⚙️ Setup

### 1 — Prerequisites

- Python **3.9+**
- A Binance Futures **Testnet** account → https://testnet.binancefuture.com

### 2 — Install dependencies

```bash
# From the project root (trading_bot/)
pip install -r requirements.txt
```

### 3 — Configure API keys

**Recommended:** create a `.env` file in the project root:

```dotenv
BINANCE_API_KEY=your_testnet_api_key_here
BINANCE_API_SECRET=your_testnet_api_secret_here
```

The bot loads this file automatically via `python-dotenv`.

**Alternative:** export environment variables in your shell:

```bash
export BINANCE_API_KEY="your_testnet_api_key_here"
export BINANCE_API_SECRET="your_testnet_api_secret_here"
```

**Or** pass keys directly on the command line (not recommended for production):

```bash
python cli.py ... --api-key <key> --api-secret <secret>
```

---

## 🚀 Running the CLI

### MARKET order (buy 0.001 BTC)

```bash
python cli.py \
  --symbol BTCUSDT \
  --side   BUY \
  --type   MARKET \
  --quantity 0.001
```

### LIMIT order (sell 0.1 ETH at $3,000)

```bash
python cli.py \
  --symbol   ETHUSDT \
  --side     SELL \
  --type     LIMIT \
  --quantity 0.1 \
  --price    3000
```

### STOP_LIMIT order (buy BTC when price drops to $67,500, execute at $68,000)

```bash
python cli.py \
  --symbol     BTCUSDT \
  --side       BUY \
  --type       STOP_LIMIT \
  --quantity   0.001 \
  --price      68000 \
  --stop-price 67500
```

---

## 📤 Example Output

```
──────────────────────────────────────────────────────
  📋  ORDER REQUEST SUMMARY
──────────────────────────────────────────────────────
  Symbol    : BTCUSDT
  Side      : BUY
  Type      : MARKET
  Quantity  : 0.001
──────────────────────────────────────────────────────

──────────────────────────────────────────────────────
  ✅  ORDER PLACED SUCCESSFULLY
──────────────────────────────────────────────────────
  Order ID       : 3951680029
  Client Order ID: x-abc123...
  Status         : FILLED
  Symbol         : BTCUSDT
  Side           : BUY
  Type           : MARKET
  Orig Qty       : 0.001
  Executed Qty   : 0.001
  Avg Price      : 67432.10
──────────────────────────────────────────────────────
```

---

## 📜 Logs

All API requests, responses, and errors are written to **`bot.log`** in the working directory (rotating, max 5 MB × 3 backups). Console output only shows warnings and above to keep the CLI clean.

```bash
tail -f bot.log   # live log stream
```

---

## 🔧 CLI Reference

| Flag | Required | Description |
|------|----------|-------------|
| `--symbol` / `-s` | ✅ | Trading pair, e.g. `BTCUSDT` |
| `--side` | ✅ | `BUY` or `SELL` |
| `--type` / `-t` | ✅ | `MARKET`, `LIMIT`, or `STOP_LIMIT` |
| `--quantity` / `-q` | ✅ | Positive number |
| `--price` / `-p` | LIMIT / STOP_LIMIT | Limit execution price |
| `--stop-price` | STOP_LIMIT | Stop trigger price |
| `--api-key` | Optional | Override env var |
| `--api-secret` | Optional | Override env var |

---

## 📌 Assumptions

1. **Testnet only** — the base URL is hard-coded to `https://testnet.binancefuture.com`. For live trading, change `BASE_URL` in `bot/client.py`.
2. **USDT-M Futures** — the `/fapi/v1/order` endpoint is used. COIN-M futures use `/dapi/v1/order`.
3. **Quantity precision** — you are responsible for providing a quantity that meets the symbol's `LOT_SIZE` filter (check via the Exchange Info endpoint). The bot forwards whatever value you supply.
4. **STOP_LIMIT** maps to Binance Futures `type=STOP`, which is a stop-limit order (not `STOP_MARKET`).
5. **Time-in-force** defaults to `GTC` (Good-Till-Cancelled) for LIMIT and STOP_LIMIT orders.
6. **Retry logic** — up to 3 attempts with exponential back-off (1 s, 2 s, 4 s) on network errors. API-level errors (e.g. invalid symbol) are **not** retried.
7. **python-dotenv** is optional — if not installed, keys must come from environment variables or CLI flags.

---

## 🏗️ Architecture Overview

```
cli.py  ──▶  validators.py   (raise ValueError on bad input)
        ──▶  orders.py       (build params, call client, return OrderResult)
                └──▶  client.py   (sign request, HTTP POST, handle errors)
        ──▶  logging_config  (wire up file + console handlers at startup)
```

---

## 🛡️ Error Handling

| Scenario | Behaviour |
|----------|-----------|
| Missing / bad CLI argument | Validation error printed; exit code 1 |
| Invalid symbol / insufficient balance | `BinanceAPIError` with code + message |
| Network timeout / connection refused | Retried up to 3 times, then `BinanceNetworkError` |
| Missing API credentials | Descriptive error message; exit code 1 |
| Unexpected exception | Full traceback logged to `bot.log`; user-friendly message printed |
