"""Base strategy class"""

from abc import ABC, abstractmethod
from typing import Dict, Optional
import pandas as pd
from utils.logger import setup_logger

logger = setup_logger('strategy')


class BaseStrategy(ABC):
    """Abstract base class for all trading strategies"""
    
    def __init__(self, name: str, parameters: Optional[Dict] = None):
        self.name = name
        self.parameters = parameters or {}
        self.enabled = True
        self.performance_stats = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_profit': 0,
            'total_loss': 0
        }
    
    @abstractmethod
    def generate_signal(self, data: pd.DataFrame, current_price: float) -> Dict:
        """Generate trading signal
        
        Args:
            data: Historical price data
            current_price: Current market price
            
        Returns:
            Signal dictionary with action, strength, confidence
        """
        pass
    
    @abstractmethod
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators for the strategy
        
        Args:
            data: Price data
            
        Returns:
            DataFrame with added indicators
        """
        pass
    
    def update_performance(self, result: Dict):
        """Update strategy performance statistics
        
        Args:
            result: Trade result dictionary
        """
        self.performance_stats['total_trades'] += 1
        
        if result.get('profit', 0) > 0:
            self.performance_stats['winning_trades'] += 1
            self.performance_stats['total_profit'] += result['profit']
        else:
            self.performance_stats['losing_trades'] += 1
            self.performance_stats['total_loss'] += abs(result['profit'])
    
    def get_win_rate(self) -> float:
        """Calculate win rate"""
        total = self.performance_stats['total_trades']
        if total == 0:
            return 0.0
        
        return self.performance_stats['winning_trades'] / total
    
    def get_profit_factor(self) -> float:
        """Calculate profit factor"""
        if self.performance_stats['total_loss'] == 0:
            return float('inf')
        
        return self.performance_stats['total_profit'] / self.performance_stats['total_loss']
    
    def reset_performance(self):
        """Reset performance statistics"""
        self.performance_stats = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_profit': 0,
            'total_loss': 0
        }