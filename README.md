# ⚜ Forex Gold (OANDA XAU/USD) -> Groww MCX Gold Algo Paper Trader

A cross-platform algorithmic trading & paper execution application that fetches Forex Gold (`XAU/USD`) market data from **OANDA Demo/Live API**, evaluates strategy signals on configurable candle timeframes (**1-min**, **5-min**, etc.), and executes paper trades on **MCX Gold Mini contracts (`GOLDM`)** simulating Groww order execution.

---

## 🌟 Key Features

1. **OANDA Forex Gold Integration**:
   - Connects to OANDA v20 REST API (`api-fxpractice.oanda.com` for demo/practice accounts).
   - Configurable candle granularities: **1 Minute (`M1`)**, **5 Minutes (`M5`)**, **15 Minutes (`M15`)**, **1 Hour (`H1`)**.
   - Built-in realistic mock data generator fallback when API key is in practice/demo mode or offline.

2. **Groww MCX Gold Mini (`GOLDM`) Paper Trading Engine**:
   - **Contract Specification**: 1 Lot = 100 grams of Gold (Quoted in INR per 10 grams).
   - **XAU/USD to MCX Conversion**: Converts Forex Gold price ($/troy oz) to MCX Gold price (₹/10g) using USD/INR exchange rate and import duty multipliers.
   - **Account Balance**: Fully configurable starting balance (e.g. ₹5,00,000).
   - **Risk Management**: Dynamic Stop-Loss (%) and Take-Profit (%) execution on every market tick.

3. **CSV PnL & Trade Logger**:
   - Automatically appends completed trade details to `trades_log.csv`.
   - **Logged Attributes**: `Instrument Name`, `Date`, `Time`, `Signal Source`, `Strategy`, `Action`, `Lots`, `Entry Price (INR)`, `Exit Price (INR)`, `Forex Ref Price ($)`, `Trade PnL (INR)`, `Realized Total PnL (INR)`, `Account Balance (INR)`, `Status`.

4. **Alternative Testing Strategies**:
   - 📈 **EMA Crossover (`EMA_CROSSOVER`)**: Fast EMA (9) crossing Slow EMA (21) trend following on XAU/USD.
   - ⚡ **Lead-Lag Arbitrage (`LEAD_LAG_ARBITRAGE`)**: Triggers MCX Gold trades when Forex Gold moves rapidly before local MCX prices update.
   - 🔄 **Mean Reversion (`MEAN_REVERSION`)**: RSI (14) overbought/oversold spikes combined with Bollinger Bands compression.
   - 💥 **Volatility Breakout (`VOLATILITY_BREAKOUT`)**: Donchian Channel (20-period) High/Low price breakouts with ATR expansion.

5. **Modern Web GUI & Control Center**:
   - Glassmorphism dark mode interface with gold highlights.
   - TradingView Lightweight Candlestick Chart for `XAU/USD`.
   - Real-time WebSocket ticks stream (`/ws/stream`).
   - One-click CSV report download button.

---

## 🚀 Getting Started

### 1. Requirements
- Python 3.10+
- Dependencies: `fastapi`, `uvicorn`, `requests`, `pandas`, `pydantic`

### 2. Launching the Application

#### Option A: Web Dashboard UI Mode (Recommended)
Run the web application server:
```bash
python main.py
```
Open your browser and navigate to:
👉 **`http://localhost:8000`**

#### Option B: Terminal CLI Mode
Run the engine directly inside the terminal:
```bash
python main.py --cli
```

---

## 🛠 Configuration

Configuration can be updated via the Web GUI control panel or by editing `config.json`:

```json
{
    "oanda": {
        "api_token": "YOUR_OANDA_DEMO_API_TOKEN",
        "account_id": "101-001-12345678-001",
        "environment": "practice",
        "instrument": "XAU_USD",
        "timeframe": "M5"
    },
    "mcx": {
        "instrument_name": "MCX_GOLDM_OCT2026",
        "contract_size_grams": 100.0,
        "price_unit_grams": 10.0,
        "starting_balance": 500000.0,
        "usd_inr_rate": 83.5,
        "import_duty_multiplier": 1.15
    },
    "strategy": {
        "selected_strategy": "EMA_CROSSOVER",
        "fast_ema": 9,
        "slow_ema": 21,
        "stop_loss_pct": 0.5,
        "take_profit_pct": 1.0
    },
    "csv_file_path": "trades_log.csv"
}
```

---

## 🧪 Running Unit Tests

Run the automated unit test suite:
```bash
python -m unittest tests/test_algo.py
```

---

## 📊 CSV Output Format

The output file `trades_log.csv` records all trade executions:

| Instrument Name | Date | Time | Signal Source | Strategy | Action | Lots | Entry Price (INR) | Exit Price (INR) | Forex Ref Price ($) | Trade PnL (INR) | Realized Total PnL (INR) | Account Balance (INR) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `MCX_GOLDM_OCT2026` | 2026-09-06 | 11:21:53 | OANDA_XAU_USD_M5 | EMA_CROSSOVER | BUY | 1 | 78911.00 | 79822.00 | 2585.53 | 9110.00 | 9110.00 | 509110.00 | TAKE_PROFIT |
