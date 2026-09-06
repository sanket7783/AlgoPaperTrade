from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, Any, Optional
from config import StrategyConfig

class BaseStrategy(ABC):
    """
    Abstract base class for Forex Gold -> MCX Gold trading strategies.
    """
    def __init__(self, config: StrategyConfig):
        self.config = config

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def generate_signal(self, df: pd.DataFrame, current_mcx_price: float) -> Dict[str, Any]:
        """
        Processes candle DataFrame of XAU_USD and current MCX price.
        Returns signal dict:
        {
            "signal": "BUY" | "SELL" | "NEUTRAL" | "EXIT",
            "reason": str,
            "confidence": float
        }
        """
        pass
