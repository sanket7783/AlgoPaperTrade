from strategies.base_strategy import BaseStrategy
from strategies.ema_crossover import EMACrossoverStrategy
from strategies.lead_lag_arbitrage import LeadLagArbitrageStrategy
from strategies.mean_reversion import MeanReversionStrategy
from strategies.volatility_breakout import VolatilityBreakoutStrategy

STRATEGY_MAP = {
    "EMA_CROSSOVER": EMACrossoverStrategy,
    "LEAD_LAG_ARBITRAGE": LeadLagArbitrageStrategy,
    "MEAN_REVERSION": MeanReversionStrategy,
    "VOLATILITY_BREAKOUT": VolatilityBreakoutStrategy
}

def get_strategy(strategy_name: str, config):
    strategy_cls = STRATEGY_MAP.get(strategy_name.upper(), EMACrossoverStrategy)
    return strategy_cls(config)
