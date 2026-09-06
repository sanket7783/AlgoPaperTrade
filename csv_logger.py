import os
import csv
from datetime import datetime
from typing import Dict, Any, List

class CSVTradeLogger:
    FIELDNAMES = [
        "Instrument Name",
        "Date",
        "Time",
        "Signal Source",
        "Strategy",
        "Action",
        "Lots",
        "Entry Price (INR)",
        "Exit Price (INR)",
        "Forex Ref Price ($)",
        "Trade PnL (INR)",
        "Realized Total PnL (INR)",
        "Account Balance (INR)",
        "Status"
    ]

    def __init__(self, filepath: str = "trades_log.csv"):
        self.filepath = filepath
        self._ensure_header()

    def _ensure_header(self):
        file_exists = os.path.exists(self.filepath)
        if not file_exists:
            with open(self.filepath, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
                writer.writeheader()

    def log_trade(
        self,
        instrument_name: str,
        signal_source: str,
        strategy: str,
        action: str,
        lots: int,
        entry_price: float,
        exit_price: float,
        forex_ref_price: float,
        trade_pnl: float,
        realized_total_pnl: float,
        account_balance: float,
        status: str,
        timestamp: datetime = None
    ) -> Dict[str, Any]:
        if timestamp is None:
            timestamp = datetime.now()

        record = {
            "Instrument Name": instrument_name,
            "Date": timestamp.strftime("%Y-%m-%d"),
            "Time": timestamp.strftime("%H:%M:%S"),
            "Signal Source": signal_source,
            "Strategy": strategy,
            "Action": action,
            "Lots": lots,
            "Entry Price (INR)": round(entry_price, 2),
            "Exit Price (INR)": round(exit_price, 2),
            "Forex Ref Price ($)": round(forex_ref_price, 2),
            "Trade PnL (INR)": round(trade_pnl, 2),
            "Realized Total PnL (INR)": round(realized_total_pnl, 2),
            "Account Balance (INR)": round(account_balance, 2),
            "Status": status
        }

        with open(self.filepath, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
            writer.writerow(record)

        return record

    def read_all_trades(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.filepath):
            return []
        trades = []
        with open(self.filepath, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                trades.append(dict(row))
        return trades
