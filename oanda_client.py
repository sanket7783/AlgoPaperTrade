import time
import random
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from app_logger import log_event

class OandaClient:
    """
    OANDA v20 REST Client for fetching Forex Gold (XAU_USD) data.
    Includes built-in realistic market data generator fallback when API token is placeholder or offline.
    """
    def __init__(self, api_token: str = "DEMO_TOKEN_PLACEHOLDER", account_id: str = "", environment: str = "practice"):
        self.api_token = api_token
        self.account_id = account_id
        self.environment = environment.lower()
        
        if self.environment == "live":
            self.base_url = "https://api-fxtrade.oanda.com/v3"
        else:
            self.base_url = "https://api-fxpractice.oanda.com/v3"
            
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        self._simulated_price = 2510.50
        self._simulated_trend = 0.05

    @property
    def is_live_api_active(self) -> bool:
        return bool(self.api_token and self.api_token != "DEMO_TOKEN_PLACEHOLDER" and len(self.api_token) > 10)

    def fetch_candles(self, instrument: str = "XAU_USD", granularity: str = "M5", count: int = 100) -> pd.DataFrame:
        """
        Fetch OHLCV candle data from OANDA API or generate realistic simulated candles.
        """
        if self.is_live_api_active:
            try:
                url = f"{self.base_url}/instruments/{instrument}/candles"
                params = {"granularity": granularity, "count": count, "price": "M"}
                res = requests.get(url, headers=self.headers, params=params, timeout=5)
                if res.status_code == 200:
                    data = res.json()
                    candles = data.get("candles", [])
                    records = []
                    for c in candles:
                        mid = c.get("mid", {})
                        records.append({
                            "time": c.get("time"),
                            "open": float(mid.get("o")),
                            "high": float(mid.get("h")),
                            "low": float(mid.get("l")),
                            "close": float(mid.get("c")),
                            "volume": int(c.get("volume", 0))
                        })
                    df = pd.DataFrame(records)
                    df['time'] = pd.to_datetime(df['time'])
                    log_event("INFO", "POLLING", f"OANDA API Poll: Fetched {len(df)} candles for {instrument} ({granularity}) | Latest Close: ${df['close'].iloc[-1]:.2f}")
                    return df
            except Exception as e:
                log_event("WARNING", "POLLING", f"OANDA API Request failed: {e}. Using fallback simulation.")

        # Fallback Simulation Mode
        df = self._generate_simulated_candles(instrument, granularity, count)
        log_event("INFO", "POLLING", f"OANDA Poll (Demo Mode): Fetched {len(df)} candles for {instrument} ({granularity}) | Latest Price: ${df['close'].iloc[-1]:.2f}")
        return df

    def fetch_latest_price(self, instrument: str = "XAU_USD") -> float:
        """
        Fetch the current mid price for XAU_USD.
        """
        if self.is_live_api_active:
            try:
                url = f"{self.base_url}/instruments/{instrument}/candles"
                params = {"granularity": "M1", "count": 1, "price": "M"}
                res = requests.get(url, headers=self.headers, params=params, timeout=3)
                if res.status_code == 200:
                    candles = res.json().get("candles", [])
                    if candles:
                        price = float(candles[-1]["mid"]["c"])
                        log_event("INFO", "POLLING", f"OANDA Spot Price Poll: {instrument} = ${price:.2f}")
                        return price
            except Exception:
                pass

        noise = random.gauss(0, 0.45)
        self._simulated_price = max(1800.0, self._simulated_price + self._simulated_trend + noise)
        price = round(self._simulated_price, 2)
        log_event("INFO", "POLLING", f"OANDA Spot Price Poll (Demo Mode): {instrument} = ${price:.2f}")
        return price

    def _generate_simulated_candles(self, instrument: str, granularity: str, count: int) -> pd.DataFrame:
        delta_minutes = 5
        if granularity == "M1": delta_minutes = 1
        elif granularity == "M15": delta_minutes = 15
        elif granularity == "M30": delta_minutes = 30
        elif granularity == "H1": delta_minutes = 60

        now = datetime.now()
        start_time = now - timedelta(minutes=delta_minutes * count)
        price = self._simulated_price
        records = []
        volatility = 1.2 if granularity in ["M1", "M5"] else 2.5
        trend = (random.random() - 0.49) * 0.2

        for i in range(count):
            candle_time = start_time + timedelta(minutes=delta_minutes * i)
            open_p = price
            change = random.gauss(trend, volatility)
            close_p = open_p + change
            high_p = max(open_p, close_p) + abs(random.gauss(0, volatility * 0.5))
            low_p = min(open_p, close_p) - abs(random.gauss(0, volatility * 0.5))
            records.append({
                "time": candle_time,
                "open": round(open_p, 2),
                "high": round(high_p, 2),
                "low": round(low_p, 2),
                "close": round(close_p, 2),
                "volume": random.randint(150, 2500)
            })
            price = close_p

        self._simulated_price = price
        return pd.DataFrame(records)
