import pandas as pd
from typing import Dict, Any
from strategies.base_strategy import BaseStrategy
from config import StrategyConfig

class EMACrossoverStrategy(BaseStrategy):
    @property
    def name(self) -> str:
        return "EMA_CROSSOVER"

    def generate_signal(self, df: pd.DataFrame, current_mcx_price: float) -> Dict[str, Any]:
        if df is None or len(df) < max(self.config.fast_ema, self.config.slow_ema) + 2:
            return {"signal": "NEUTRAL", "reason": "Insufficient candles", "confidence": 0.0}

        df = df.copy()
        df['fast_ema'] = df['close'].ewm(span=self.config.fast_ema, adjust=False).mean()
        df['slow_ema'] = df['close'].ewm(span=self.config.slow_ema, adjust=False).mean()

        curr_fast = df['fast_ema'].iloc[-1]
        curr_slow = df['slow_ema'].iloc[-1]
        prev_fast = df['fast_ema'].iloc[-2]
        prev_slow = df['slow_ema'].iloc[-2]

        signal = "NEUTRAL"
        reason = f"Fast EMA ({curr_fast:.2f}) & Slow EMA ({curr_slow:.2f})"
        confidence = 0.0

        # Bullish Crossover
        if prev_fast <= prev_slow and curr_fast > curr_slow:
            signal = "BUY"
            reason = f"Bullish Crossover: Fast EMA ({curr_fast:.2f}) crossed above Slow EMA ({curr_slow:.2f})"
            confidence = min(1.0, abs(curr_fast - curr_slow) / curr_slow * 100)

        # Bearish Crossover
        elif prev_fast >= prev_slow and curr_fast < curr_slow:
            signal = "SELL"
            reason = f"Bearish Crossover: Fast EMA ({curr_fast:.2f}) crossed below Slow EMA ({curr_slow:.2f})"
            confidence = min(1.0, abs(curr_fast - curr_slow) / curr_slow * 100)

        return {
            "signal": signal,
            "reason": reason,
            "confidence": round(confidence, 4),
            "fast_ema": round(curr_fast, 2),
            "slow_ema": round(curr_slow, 2)
        }
