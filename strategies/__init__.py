"""Trading strategies module"""

from .base import BaseStrategy
from .trend_following import TrendFollowingStrategy
from .mean_reversion import MeanReversionStrategy
from .breakout import BreakoutStrategy
from .strategy_manager import StrategyManager

__all__ = [
    'BaseStrategy',
    'TrendFollowingStrategy',
    'MeanReversionStrategy',
    'BreakoutStrategy',
    'StrategyManager'
]