import pandas as pd
from typing import Dict, Any
from strategies.base_strategy import BaseStrategy
from config import StrategyConfig

class LeadLagArbitrageStrategy(BaseStrategy):
    @property
    def name(self) -> str:
        return "LEAD_LAG_ARBITRAGE"

    def generate_signal(self, df: pd.DataFrame, current_mcx_price: float) -> Dict[str, Any]:
        if df is None or len(df) < 5:
            return {"signal": "NEUTRAL", "reason": "Insufficient candles", "confidence": 0.0}

        # Calculate Forex Gold % change over last 3 candles
        forex_start = df['close'].iloc[-4]
        forex_curr = df['close'].iloc[-1]
        forex_pct_change = ((forex_curr - forex_start) / forex_start) * 100.0

        threshold = self.config.lead_lag_threshold_pct

        signal = "NEUTRAL"
        reason = f"Forex move: {forex_pct_change:+.3f}% (Threshold: {threshold}%)"
        confidence = 0.0

        if forex_pct_change >= threshold:
            signal = "BUY"
            reason = f"Forex Lead Impulse UP ({forex_pct_change:+.3f}%). Expecting MCX Gold catch-up."
            confidence = min(1.0, abs(forex_pct_change) / (threshold * 2))
        elif forex_pct_change <= -threshold:
            signal = "SELL"
            reason = f"Forex Lead Impulse DOWN ({forex_pct_change:+.3f}%). Expecting MCX Gold sell-off."
            confidence = min(1.0, abs(forex_pct_change) / (threshold * 2))

        return {
            "signal": signal,
            "reason": reason,
            "confidence": round(confidence, 4),
            "forex_move_pct": round(forex_pct_change, 3)
        }
