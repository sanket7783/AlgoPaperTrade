import os
import json
from dataclasses import dataclass, field, asdict
from typing import Dict, Any

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

@dataclass
class OandaConfig:
    api_token: str = field(default_factory=lambda: os.getenv("OANDA_API_TOKEN", "DEMO_TOKEN_PLACEHOLDER"))
    account_id: str = field(default_factory=lambda: os.getenv("OANDA_ACCOUNT_ID", "101-001-12345678-001"))
    environment: str = field(default_factory=lambda: os.getenv("OANDA_ENVIRONMENT", "practice"))
    instrument: str = "XAU_USD"
    timeframe: str = "M5"  # M1, M5, M15, M30, H1

@dataclass
class McxConfig:
    instrument_name: str = "MCX_GOLDGUINEA_OCT2026"
    groww_trading_symbol: str = "GOLDGUINEA26OCTFUT"
    groww_api_key: str = field(default_factory=lambda: os.getenv("GROWW_API_KEY", ""))
    groww_api_secret: str = field(default_factory=lambda: os.getenv("GROWW_API_SECRET", ""))
    groww_access_token: str = field(default_factory=lambda: os.getenv("GROWW_ACCESS_TOKEN", ""))
    contract_size_grams: float = 8.0    # 1 Lot Gold Guinea = 8 grams
    price_unit_grams: float = 8.0       # Quoted per Guinea (8 grams) in INR
    tick_size: float = 1.0              # Tick size ₹1 per Guinea
    starting_balance: float = 25000.0   # Configured for ₹25,000 capital
    usd_inr_rate: float = 83.5          # Default USD/INR exchange rate
    import_duty_multiplier: float = 1.15# Duty/Premium factor (~15% tax/duty)

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
                cfg = cls(
                    oanda=OandaConfig(**data.get("oanda", {})),
                    mcx=McxConfig(**data.get("mcx", {})),
                    strategy=StrategyConfig(**data.get("strategy", {})),
                    csv_file_path=data.get("csv_file_path", "trades_log.csv"),
                    update_interval_sec=data.get("update_interval_sec", 2.0)
                )
                # Fall back to env variables if json values are empty
                if not cfg.mcx.groww_access_token and os.getenv("GROWW_ACCESS_TOKEN"):
                    cfg.mcx.groww_access_token = os.getenv("GROWW_ACCESS_TOKEN")
                if (not cfg.oanda.api_token or cfg.oanda.api_token == "DEMO_TOKEN_PLACEHOLDER") and os.getenv("OANDA_API_TOKEN"):
                    cfg.oanda.api_token = os.getenv("OANDA_API_TOKEN")
                return cfg
        return cls()
