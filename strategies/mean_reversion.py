import pandas as pd
import numpy as np
from typing import Dict, Any
from strategies.base_strategy import BaseStrategy
from config import StrategyConfig

class MeanReversionStrategy(BaseStrategy):
    @property
    def name(self) -> str:
        return "MEAN_REVERSION"

    def generate_signal(self, df: pd.DataFrame, current_mcx_price: float) -> Dict[str, Any]:
        if df is None or len(df) < max(self.config.rsi_period, self.config.bollinger_period) + 2:
            return {"signal": "NEUTRAL", "reason": "Insufficient candles", "confidence": 0.0}

        df = df.copy()
        
        # Calculate RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.config.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.config.rsi_period).mean()
        rs = gain / (loss + 1e-9)
        df['rsi'] = 100 - (100 / (1 + rs))

        # Calculate Bollinger Bands
        df['bb_mid'] = df['close'].rolling(window=self.config.bollinger_period).mean()
        std = df['close'].rolling(window=self.config.bollinger_period).std()
        df['bb_upper'] = df['bb_mid'] + (self.config.bollinger_std * std)
        df['bb_lower'] = df['bb_mid'] - (self.config.bollinger_std * std)

        curr_close = df['close'].iloc[-1]
        curr_rsi = df['rsi'].iloc[-1]
        curr_upper = df['bb_upper'].iloc[-1]
        curr_lower = df['bb_lower'].iloc[-1]

        signal = "NEUTRAL"
        reason = f"RSI: {curr_rsi:.1f}, BB Lower: {curr_lower:.2f}, BB Upper: {curr_upper:.2f}"
        confidence = 0.0

        # Oversold + Lower BB Reversion Signal
        if curr_rsi <= self.config.rsi_oversold or curr_close <= curr_lower:
            signal = "BUY"
            reason = f"Oversold Reversion: RSI={curr_rsi:.1f} <= {self.config.rsi_oversold} or Price <= BB Lower"
            confidence = min(1.0, (self.config.rsi_oversold - curr_rsi + 5) / 25)

        # Overbought + Upper BB Reversion Signal
        elif curr_rsi >= self.config.rsi_overbought or curr_close >= curr_upper:
            signal = "SELL"
            reason = f"Overbought Reversion: RSI={curr_rsi:.1f} >= {self.config.rsi_overbought} or Price >= BB Upper"
            confidence = min(1.0, (curr_rsi - self.config.rsi_overbought + 5) / 25)

        return {
            "signal": signal,
            "reason": reason,
            "confidence": round(max(0.0, confidence), 4),
            "rsi": round(curr_rsi, 2),
            "bb_lower": round(curr_lower, 2),
            "bb_upper": round(curr_upper, 2)
        }
