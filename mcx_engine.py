from datetime import datetime
from typing import Dict, Any, Optional, List
from config import McxConfig
from csv_logger import CSVTradeLogger
from app_logger import log_event

class MCXPosition:
    def __init__(self, instrument_name: str, side: str, lots: int, entry_price: float, forex_entry_price: float, entry_time: datetime):
        self.instrument_name = instrument_name
        self.side = side.upper()
        self.lots = lots
        self.entry_price = entry_price
        self.forex_entry_price = forex_entry_price
        self.entry_time = entry_time
        self.stop_loss: Optional[float] = None
        self.take_profit: Optional[float] = None

    def calculate_mtm(self, current_price: float, contract_size_grams: float = 100.0, price_unit_grams: float = 10.0) -> float:
        multiplier = (contract_size_grams / price_unit_grams) * self.lots
        price_diff = (current_price - self.entry_price) if self.side == "BUY" else (self.entry_price - current_price)
        return price_diff * multiplier

class MCXPaperTradingEngine:
    """
    Paper Trading Execution Engine simulating Groww MCX Gold Mini (GOLDM) orders.
    """
    def __init__(self, config: McxConfig, csv_logger: CSVTradeLogger):
        self.config = config
        self.csv_logger = csv_logger
        self.account_balance = config.starting_balance
        self.realized_pnl = 0.0
        self.current_position: Optional[MCXPosition] = None
        self.trade_history: List[Dict[str, Any]] = []

    def convert_xau_to_mcx(self, xau_usd_price: float) -> float:
        grams_per_oz = 31.1034768
        price_per_gram_usd = xau_usd_price / grams_per_oz
        price_per_10g_inr = (price_per_gram_usd * self.config.price_unit_grams * 
                             self.config.usd_inr_rate * self.config.import_duty_multiplier)
        tick = self.config.tick_size
        return round(round(price_per_10g_inr / tick) * tick, 2)

    def place_order(
        self,
        side: str,
        lots: int,
        mcx_price: float,
        forex_price: float,
        signal_source: str,
        strategy_name: str,
        stop_loss_pct: Optional[float] = None,
        take_profit_pct: Optional[float] = None
    ) -> Dict[str, Any]:
        side = side.upper()
        now = datetime.now()

        log_event("INFO", "ORDER", f"Order Request Received: {side} {lots} Lot(s) of {self.config.instrument_name} @ ₹{mcx_price:,.2f} (Strategy: {strategy_name})")

        # Close existing opposite position if present
        if self.current_position is not None:
            if self.current_position.side != side:
                log_event("INFO", "ORDER", f"Position Reversal Detected ({self.current_position.side} -> {side}). Closing existing position.")
                self.close_position(mcx_price, forex_price, strategy_name, signal_source, reason="SIGNAL_REVERSAL")
            else:
                log_event("WARNING", "ORDER", f"Order Rejected: Already holding active {side} position.")
                return {"status": "REJECTED", "reason": "Already in same side position"}

        # Margin check
        contract_val = mcx_price * (self.config.contract_size_grams / self.config.price_unit_grams) * lots
        required_margin = contract_val * 0.10
        if required_margin > self.account_balance:
            log_event("ERROR", "RISK", f"Order Rejected: Insufficient balance. Required Margin: ₹{required_margin:,.2f}, Available: ₹{self.account_balance:,.2f}")
            return {
                "status": "REJECTED",
                "reason": f"Insufficient balance. Required Margin: ₹{required_margin:.2f}, Available: ₹{self.account_balance:.2f}"
            }

        position = MCXPosition(
            instrument_name=self.config.instrument_name,
            side=side,
            lots=lots,
            entry_price=mcx_price,
            forex_entry_price=forex_price,
            entry_time=now
        )

        if stop_loss_pct:
            sl_delta = mcx_price * (stop_loss_pct / 100.0)
            position.stop_loss = (mcx_price - sl_delta) if side == "BUY" else (mcx_price + sl_delta)

        if take_profit_pct:
            tp_delta = mcx_price * (take_profit_pct / 100.0)
            position.take_profit = (mcx_price + tp_delta) if side == "BUY" else (mcx_price - tp_delta)

        self.current_position = position

        log_event("INFO", "BOOKING", f"ORDER FILLED & POSITION OPENED: {side} {lots} Lot(s) {position.instrument_name} @ ₹{mcx_price:,.2f} | SL: ₹{position.stop_loss or 0:,.2f} | TP: ₹{position.take_profit or 0:,.2f}")

        trade_info = {
            "status": "OPENED",
            "side": side,
            "lots": lots,
            "entry_price": mcx_price,
            "forex_price": forex_price,
            "time": now.isoformat(),
            "stop_loss": position.stop_loss,
            "take_profit": position.take_profit
        }

        return trade_info

    def close_position(
        self,
        exit_mcx_price: float,
        exit_forex_price: float,
        strategy_name: str,
        signal_source: str,
        reason: str = "MANUAL_EXIT"
    ) -> Optional[Dict[str, Any]]:
        if self.current_position is None:
            return None

        pos = self.current_position
        trade_pnl = pos.calculate_mtm(exit_mcx_price, self.config.contract_size_grams, self.config.price_unit_grams)
        
        self.realized_pnl += trade_pnl
        self.account_balance += trade_pnl
        self.current_position = None

        log_event("INFO", "BOOKING", f"POSITION CLOSED ({reason}): {pos.side} {pos.lots} Lot(s) @ Entry ₹{pos.entry_price:,.2f} -> Exit ₹{exit_mcx_price:,.2f} | Trade PnL: ₹{trade_pnl:+,.2f} | New Account Balance: ₹{self.account_balance:,.2f}")

        log_entry = self.csv_logger.log_trade(
            instrument_name=pos.instrument_name,
            signal_source=signal_source,
            strategy=strategy_name,
            action=pos.side,
            lots=pos.lots,
            entry_price=pos.entry_price,
            exit_price=exit_mcx_price,
            forex_ref_price=exit_forex_price,
            trade_pnl=trade_pnl,
            realized_total_pnl=self.realized_pnl,
            account_balance=self.account_balance,
            status=reason
        )

        log_event("INFO", "SYSTEM", f"CSV Log Appended: {pos.instrument_name} {pos.side} PnL=₹{trade_pnl:+,.2f} written to {self.csv_logger.filepath}")
        self.trade_history.append(log_entry)
        return log_entry

    def update_tick(
        self,
        mcx_price: float,
        forex_price: float,
        strategy_name: str,
        signal_source: str
    ) -> Optional[Dict[str, Any]]:
        if self.current_position is None:
            return None

        pos = self.current_position

        # Check Stop Loss
        if pos.stop_loss is not None:
            if (pos.side == "BUY" and mcx_price <= pos.stop_loss) or (pos.side == "SELL" and mcx_price >= pos.stop_loss):
                log_event("WARNING", "RISK", f"STOP LOSS TRIGGERED for {pos.side} position @ ₹{mcx_price:,.2f} (SL Target: ₹{pos.stop_loss:,.2f})")
                return self.close_position(mcx_price, forex_price, strategy_name, signal_source, reason="STOP_LOSS")

        # Check Take Profit
        if pos.take_profit is not None:
            if (pos.side == "BUY" and mcx_price >= pos.take_profit) or (pos.side == "SELL" and mcx_price <= pos.take_profit):
                log_event("INFO", "RISK", f"TAKE PROFIT TRIGGERED for {pos.side} position @ ₹{mcx_price:,.2f} (TP Target: ₹{pos.take_profit:,.2f})")
                return self.close_position(mcx_price, forex_price, strategy_name, signal_source, reason="TAKE_PROFIT")

        return None

    def get_status(self, current_mcx_price: float) -> Dict[str, Any]:
        unrealized_pnl = 0.0
        pos_data = None

        if self.current_position:
            unrealized_pnl = self.current_position.calculate_mtm(
                current_mcx_price, self.config.contract_size_grams, self.config.price_unit_grams
            )
            pos_data = {
                "instrument": self.current_position.instrument_name,
                "side": self.current_position.side,
                "lots": self.current_position.lots,
                "entry_price": self.current_position.entry_price,
                "forex_entry_price": self.current_position.forex_entry_price,
                "current_price": current_mcx_price,
                "unrealized_pnl": round(unrealized_pnl, 2),
                "stop_loss": self.current_position.stop_loss,
                "take_profit": self.current_position.take_profit,
                "entry_time": self.current_position.entry_time.strftime("%H:%M:%S")
            }

        return {
            "account_balance": round(self.account_balance, 2),
            "realized_pnl": round(self.realized_pnl, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "total_equity": round(self.account_balance + unrealized_pnl, 2),
            "open_position": pos_data
        }
