import time
import asyncio
import threading
import pandas as pd
from datetime import datetime, time as dtime
from typing import Dict, Any, List, Optional
from config import AppConfig
from oanda_client import OandaClient
from groww_mcx_client import GrowwMCXClient
from csv_logger import CSVTradeLogger
from mcx_engine import MCXPaperTradingEngine
from strategies import get_strategy

def is_mcx_market_open(check_time: Optional[datetime] = None) -> bool:
    """
    Checks if MCX India market is open.
    MCX Commodity Trading Hours: 09:00 AM to 11:30 PM IST (Mon-Fri).
    """
    if check_time is None:
        check_time = datetime.now()
    
    # Check weekend (5 = Saturday, 6 = Sunday)
    if check_time.weekday() in [5, 6]:
        return False

    current_time = check_time.time()
    market_start = dtime(9, 0, 0)
    market_close = dtime(23, 30, 0)

    return market_start <= current_time <= market_close

class AlgoTradingEngine:
    """
    Main cross-platform Trading Engine connecting OANDA Forex Gold signals with MCX Gold Mini Groww paper execution.
    """
    def __init__(self, config: AppConfig):
        self.config = config
        self.oanda_client = OandaClient(
            api_token=config.oanda.api_token,
            account_id=config.oanda.account_id,
            environment=config.oanda.environment
        )
        self.groww_client = GrowwMCXClient(
            api_key=config.mcx.groww_api_key,
            api_secret=config.mcx.groww_api_secret,
            access_token=config.mcx.groww_access_token
        )
        self.csv_logger = CSVTradeLogger(filepath=config.csv_file_path)
        self.mcx_engine = MCXPaperTradingEngine(config=config.mcx, csv_logger=self.csv_logger)
        
        self.is_running = False
        self.auto_trade_enabled = True
        self.enforce_market_hours = getattr(config, "enforce_market_hours", True)
        self.live_market_only = getattr(config, "live_market_only", True)
        self.current_strategy = get_strategy(config.strategy.selected_strategy, config.strategy)
        
        # State metrics
        self.latest_forex_price = 2500.0
        self.latest_mcx_price = 77000.0
        self.mcx_data_source = "OANDA_CONVERTED"
        self.latest_signal = {"signal": "NEUTRAL", "reason": "Engine initialized", "confidence": 0.0}
        self.latest_candles: List[Dict[str, Any]] = []
        self.token_status: Dict[str, Any] = {
            "oanda": {"valid": False, "message": "Not verified yet"},
            "groww": {"valid": False, "message": "Not verified yet"}
        }

    def check_all_tokens(self) -> Dict[str, Any]:
        """
        Actively checks validity of both OANDA and Groww tokens.
        """
        oanda_valid, oanda_msg, _ = self.oanda_client.validate_token()
        groww_valid, groww_msg, _ = self.groww_client.validate_token()
        self.token_status = {
            "oanda": {"valid": oanda_valid, "message": oanda_msg},
            "groww": {"valid": groww_valid, "message": groww_msg}
        }
        return self.token_status

    def update_config(self, new_config: AppConfig):
        """
        Dynamically updates system configuration and re-authenticates API clients.
        """
        self.config = new_config
        self.enforce_market_hours = getattr(new_config, "enforce_market_hours", True)
        self.live_market_only = getattr(new_config, "live_market_only", True)

        self.oanda_client.update_credentials(
            api_token=new_config.oanda.api_token,
            account_id=new_config.oanda.account_id,
            environment=new_config.oanda.environment
        )
        
        self.groww_client.access_token = new_config.mcx.groww_access_token
        self.groww_client.api_key = new_config.mcx.groww_api_key
        self.groww_client.api_secret = new_config.mcx.groww_api_secret
        self.groww_client.init_groww_sdk()

        self.mcx_engine.config = new_config.mcx
        self.current_strategy = get_strategy(new_config.strategy.selected_strategy, new_config.strategy)

        # Refresh token validation status
        self.check_all_tokens()

    def process_tick(self) -> Dict[str, Any]:
        """
        Single execution tick:
        1. Checks market hours and live market data requirements.
        2. Fetches Forex XAU_USD candles from OANDA (live-only when configured).
        3. Fetches live MCX price from Groww API.
        4. If in Live Market Only mode and data is missing or markets closed, blocks synthetic simulation.
        5. Evaluates current strategy signals and checks Stop-loss/Take-profit on open positions.
        6. Automatically executes paper orders on BUY/SELL signals.
        """
        now = datetime.now()
        market_open = is_mcx_market_open(now)
        timeframe = self.config.oanda.timeframe
        instrument = self.config.oanda.instrument
        live_only = getattr(self.config, "live_market_only", True)
        
        # 1. Fetch Forex Candles from OANDA
        df_candles = self.oanda_client.fetch_candles(
            instrument=instrument,
            granularity=timeframe,
            count=100,
            live_only=live_only
        )
        
        if df_candles is not None and not df_candles.empty:
            self.latest_forex_price = float(df_candles['close'].iloc[-1])
            candles_json = []
            for _, row in df_candles.tail(60).iterrows():
                candles_json.append({
                    "time": int(row['time'].timestamp()) if isinstance(row['time'], pd.Timestamp) else str(row['time']),
                    "open": float(row['open']),
                    "high": float(row['high']),
                    "low": float(row['low']),
                    "close": float(row['close']),
                    "volume": int(row['volume'])
                })
            self.latest_candles = candles_json
        else:
            latest_p = self.oanda_client.fetch_latest_price(instrument, live_only=live_only)
            if latest_p is not None:
                self.latest_forex_price = latest_p

        # 2. Get MCX Price from Groww API
        groww_price = self.groww_client.fetch_live_mcx_ltp(self.config.mcx.groww_trading_symbol)
        if groww_price is not None and groww_price > 0:
            self.latest_mcx_price = groww_price
            self.mcx_data_source = "GROWW_LIVE_API"
        elif not live_only:
            # Fallback only allowed when live_only is explicitly disabled
            self.latest_mcx_price = self.mcx_engine.convert_xau_to_mcx(self.latest_forex_price)
            self.mcx_data_source = "OANDA_DERIVED"
        else:
            self.mcx_data_source = "GROWW_UNAVAILABLE"

        # 3. Check Live-Only Requirements
        has_live_oanda = (df_candles is not None and not df_candles.empty)
        has_live_groww = (groww_price is not None and groww_price > 0)

        if live_only and (not has_live_oanda or not has_live_groww):
            reasons = []
            if not self.oanda_client.is_live_api_active:
                reasons.append("OANDA token not configured or invalid")
            elif not has_live_oanda:
                reasons.append("OANDA Forex live feed unavailable (market closed/weekend)")
                
            if not self.groww_client.is_authenticated:
                reasons.append("Groww access token not configured or invalid")
            elif not has_live_groww:
                reasons.append(f"Groww MCX quote unavailable for {self.config.mcx.groww_trading_symbol} (market closed/off-hours)")

            reason_str = "Live Market Only: " + "; ".join(reasons)
            self.latest_signal = {"signal": "NEUTRAL", "reason": reason_str, "confidence": 0.0}

            engine_status = self.mcx_engine.get_status(self.latest_mcx_price)
            return {
                "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
                "market_open": market_open,
                "enforce_market_hours": self.enforce_market_hours,
                "live_market_only": True,
                "forex_price": self.latest_forex_price,
                "mcx_price": self.latest_mcx_price,
                "mcx_source": self.mcx_data_source,
                "timeframe": timeframe,
                "strategy": self.current_strategy.name,
                "signal": self.latest_signal,
                "auto_trade_enabled": self.auto_trade_enabled,
                "engine_status": engine_status,
                "sl_tp_close_event": None,
                "executed_trade_event": None,
                "candles": self.latest_candles,
                "token_status": self.token_status
            }

        # 4. Check tick SL/TP on active positions
        sl_tp_close = self.mcx_engine.update_tick(
            mcx_price=self.latest_mcx_price,
            forex_price=self.latest_forex_price,
            strategy_name=self.current_strategy.name,
            signal_source=f"OANDA_{instrument}_{timeframe}"
        )

        # 5. Generate Strategy Signal
        signal_res = self.current_strategy.generate_signal(df_candles, self.latest_mcx_price)
        self.latest_signal = signal_res

        # If market hours enforcement is enabled and market is closed, override signal
        if self.enforce_market_hours and not market_open:
            signal_res = {"signal": "NEUTRAL", "reason": "MCX Market Closed (Open 09:00-23:30 IST Mon-Fri)", "confidence": 0.0}
            self.latest_signal = signal_res

        # 6. Automatic Trade Execution
        executed_trade = None
        if self.auto_trade_enabled and signal_res.get("signal") in ["BUY", "SELL"]:
            if not self.enforce_market_hours or market_open:
                target_side = signal_res["signal"]
                lots = self.config.strategy.max_lots_per_trade

                executed_trade = self.mcx_engine.place_order(
                    side=target_side,
                    lots=lots,
                    mcx_price=self.latest_mcx_price,
                    forex_price=self.latest_forex_price,
                    signal_source=f"OANDA_{instrument}_{timeframe}",
                    strategy_name=self.current_strategy.name,
                    stop_loss_pct=self.config.strategy.stop_loss_pct,
                    take_profit_pct=self.config.strategy.take_profit_pct
                )

        # 7. Engine state summary
        engine_status = self.mcx_engine.get_status(self.latest_mcx_price)
        
        return {
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
            "market_open": market_open,
            "enforce_market_hours": self.enforce_market_hours,
            "live_market_only": live_only,
            "forex_price": self.latest_forex_price,
            "mcx_price": self.latest_mcx_price,
            "mcx_source": self.mcx_data_source,
            "timeframe": timeframe,
            "strategy": self.current_strategy.name,
            "signal": self.latest_signal,
            "auto_trade_enabled": self.auto_trade_enabled,
            "engine_status": engine_status,
            "sl_tp_close_event": sl_tp_close,
            "executed_trade_event": executed_trade,
            "candles": self.latest_candles,
            "token_status": self.token_status
        }
