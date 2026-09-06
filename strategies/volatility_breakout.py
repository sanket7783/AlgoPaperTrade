import pandas as pd
from typing import Dict, Any
from strategies.base_strategy import BaseStrategy
from config import StrategyConfig

class VolatilityBreakoutStrategy(BaseStrategy):
    @property
    def name(self) -> str:
        return "VOLATILITY_BREAKOUT"

    def generate_signal(self, df: pd.DataFrame, current_mcx_price: float) -> Dict[str, Any]:
        period = self.config.breakout_period
        if df is None or len(df) < period + 2:
            return {"signal": "NEUTRAL", "reason": "Insufficient candles", "confidence": 0.0}

        df = df.copy()
        df['donchian_high'] = df['high'].shift(1).rolling(window=period).max()
        df['donchian_low'] = df['low'].shift(1).rolling(window=period).min()

        curr_close = df['close'].iloc[-1]
        curr_high = df['donchian_high'].iloc[-1]
        curr_low = df['donchian_low'].iloc[-1]

        signal = "NEUTRAL"
        reason = f"Donchian Range ({period}): High={curr_high:.2f}, Low={curr_low:.2f}"
        confidence = 0.0

        if curr_close > curr_high:
            signal = "BUY"
            reason = f"Volatility Breakout UP: Price ({curr_close:.2f}) broke {period}-candle High ({curr_high:.2f})"
            confidence = min(1.0, (curr_close - curr_high) / curr_close * 100)
        elif curr_close < curr_low:
            signal = "SELL"
            reason = f"Volatility Breakdown DOWN: Price ({curr_close:.2f}) broke {period}-candle Low ({curr_low:.2f})"
            confidence = min(1.0, (curr_low - curr_close) / curr_close * 100)

        return {
            "signal": signal,
            "reason": reason,
            "confidence": round(confidence, 4),
            "donchian_high": round(curr_high, 2),
            "donchian_low": round(curr_low, 2)
        }
