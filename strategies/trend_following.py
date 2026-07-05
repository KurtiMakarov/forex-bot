"""Trend Following Strategy"""

import pandas as pd
import numpy as np
from typing import Dict
from .base import BaseStrategy
from utils.logger import setup_logger

logger = setup_logger('trend_following')


class TrendFollowingStrategy(BaseStrategy):
    """Strategy that follows market trends using moving averages and momentum"""
    
    def __init__(self, parameters=None):
        default_params = {
            'short_ma': 20,
            'long_ma': 50,
            'momentum_period': 14,
            'min_trend_strength': 0.6
        }
        
        if parameters:
            default_params.update(parameters)
        
        super().__init__('Trend Following', default_params)
    
    def generate_signal(self, data: pd.DataFrame, current_price: float) -> Dict:
        """Generate trend following signal"""
        if len(data) < self.parameters['long_ma']:
            return {'action': 'hold', 'strength': 0, 'confidence': 0}
        
        # Calculate indicators
        data_with_indicators = self.calculate_indicators(data)
        
        short_ma = data_with_indicators['sma_short'].iloc[-1]
        long_ma = data_with_indicators['sma_long'].iloc[-1]
        momentum = data_with_indicators['momentum'].iloc[-1]
        
        # Determine trend direction
        if short_ma > long_ma:
            trend_direction = 'bullish'
        elif short_ma < long_ma:
            trend_direction = 'bearish'
        else:
            trend_direction = 'neutral'
        
        # Calculate trend strength
        trend_strength = abs(short_ma - long_ma) / long_ma
        
        # Generate signal
        if trend_direction == 'bullish' and momentum > 0:
            if trend_strength >= self.parameters['min_trend_strength']:
                return {
                    'action': 'buy',
                    'strength': min(trend_strength * 2, 1.0),
                    'confidence': 0.75,
                    'reason': f'Bullish trend detected (MA crossover + positive momentum)'
                }
        
        elif trend_direction == 'bearish' and momentum < 0:
            if trend_strength >= self.parameters['min_trend_strength']:
                return {
                    'action': 'sell',
                    'strength': min(trend_strength * 2, 1.0),
                    'confidence': 0.75,
                    'reason': f'Bearish trend detected (MA crossover + negative momentum)'
                }
        
        return {
            'action': 'hold',
            'strength': 0,
            'confidence': 0,
            'reason': 'No clear trend signal'
        }
    
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate trend following indicators"""
        df = data.copy()
        
        # Moving averages
        df['sma_short'] = df['close'].rolling(self.parameters['short_ma']).mean()
        df['sma_long'] = df['close'].rolling(self.parameters['long_ma']).mean()
        
        # Momentum
        df['momentum'] = df['close'].diff(self.parameters['momentum_period'])
        
        # Rate of change
        df['roc'] = df['close'].pct_change(self.parameters['momentum_period']) * 100
        
        return df