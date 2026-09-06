import os
import json
from dataclasses import dataclass, field, asdict
from typing import Dict, Any

@dataclass
class OandaConfig:
    api_token: str = "DEMO_TOKEN_PLACEHOLDER"
    account_id: str = "101-001-12345678-001"
    environment: str = "practice"  # 'practice' (demo) or 'live'
    instrument: str = "XAU_USD"
    timeframe: str = "M5"  # M1, M5, M15, M30, H1

@dataclass
class McxConfig:
    instrument_name: str = "MCX_GOLDM_OCT2026"
    groww_trading_symbol: str = "GOLDM26OCTFUT"
    groww_api_key: str = ""
    groww_api_secret: str = ""
    groww_access_token: str = ""
    contract_size_grams: float = 100.0  # 1 Lot GOLDM = 100 grams
    price_unit_grams: float = 10.0      # Price is quoted per 10 grams in INR
    tick_size: float = 1.0              # Tick size ₹1 per 10g
    starting_balance: float = 500000.0  # Configurable Account Balance (e.g. ₹5,00,000)
    usd_inr_rate: float = 83.5          # Default USD/INR exchange rate
    import_duty_multiplier: float = 1.15# Duty/Premium factor (e.g., ~15% tax/duty/local premium)

@dataclass
class StrategyConfig:
    selected_strategy: str = "EMA_CROSSOVER"  # EMA_CROSSOVER, LEAD_LAG_ARBITRAGE, MEAN_REVERSION, VOLATILITY_BREAKOUT
    fast_ema: int = 9
    slow_ema: int = 21
    rsi_period: int = 14
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0
    bollinger_period: int = 20
    bollinger_std: float = 2.0
    atr_period: int = 14
    breakout_period: int = 20
    lead_lag_threshold_pct: float = 0.15  # % divergence trigger
    stop_loss_pct: float = 0.5            # 0.5% stop loss
    take_profit_pct: float = 1.0          # 1.0% take profit
    max_lots_per_trade: int = 1

@dataclass
class AppConfig:
    oanda: OandaConfig = field(default_factory=OandaConfig)
    mcx: McxConfig = field(default_factory=McxConfig)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    csv_file_path: str = "trades_log.csv"
    update_interval_sec: float = 2.0  # Market simulation tick interval in seconds

    def save_to_file(self, filepath: str = "config.json"):
        with open(filepath, "w") as f:
            json.dump(asdict(self), f, indent=4)

    @classmethod
    def load_from_file(cls, filepath: str = "config.json") -> "AppConfig":
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                data = json.load(f)
                return cls(
                    oanda=OandaConfig(**data.get("oanda", {})),
                    mcx=McxConfig(**data.get("mcx", {})),
                    strategy=StrategyConfig(**data.get("strategy", {})),
                    csv_file_path=data.get("csv_file_path", "trades_log.csv"),
                    update_interval_sec=data.get("update_interval_sec", 2.0)
                )
        return cls()
