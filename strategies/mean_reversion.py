"""Mean Reversion Strategy"""

import pandas as pd
import numpy as np
from typing import Dict
from .base import BaseStrategy
from utils.logger import setup_logger

logger = setup_logger('mean_reversion')


class MeanReversionStrategy(BaseStrategy):
    """Strategy based on price returning to its mean"""
    
    def __init__(self, parameters=None):
        default_params = {
            'lookback_period': 20,
            'std_dev_multiplier': 2,
            'rsi_overbought': 70,
            'rsi_oversold': 30
        }
        
        if parameters:
            default_params.update(parameters)
        
        super().__init__('Mean Reversion', default_params)
    
    def generate_signal(self, data: pd.DataFrame, current_price: float) -> Dict:
        """Generate mean reversion signal"""
        if len(data) < self.parameters['lookback_period']:
            return {'action': 'hold', 'strength': 0, 'confidence': 0}
        
        # Calculate indicators
        data_with_indicators = self.calculate_indicators(data)
        
        upper_band = data_with_indicators['bb_upper'].iloc[-1]
        lower_band = data_with_indicators['bb_lower'].iloc[-1]
        rsi = data_with_indicators['rsi'].iloc[-1]
        mean = data_with_indicators['sma'].iloc[-1]
        
        # Check for overbought/oversold conditions
        if current_price <= lower_band and rsi < self.parameters['rsi_oversold']:
            distance_from_mean = (mean - current_price) / mean
            return {
                'action': 'buy',
                'strength': min(distance_from_mean * 10, 1.0),
                'confidence': 0.70,
                'reason': f'Price below lower Bollinger Band and RSI oversold ({rsi:.1f})'
            }
        
        elif current_price >= upper_band and rsi > self.parameters['rsi_overbought']:
            distance_from_mean = (current_price - mean) / mean
            return {
                'action': 'sell',
                'strength': min(distance_from_mean * 10, 1.0),
                'confidence': 0.70,
                'reason': f'Price above upper Bollinger Band and RSI overbought ({rsi:.1f})'
            }
        
        return {
            'action': 'hold',
            'strength': 0,
            'confidence': 0,
            'reason': 'Price within normal range'
        }
    
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate mean reversion indicators"""
        df = data.copy()
        
        period = self.parameters['lookback_period']
        multiplier = self.parameters['std_dev_multiplier']
        
        # Simple moving average
        df['sma'] = df['close'].rolling(period).mean()
        
        # Standard deviation
        df['std'] = df['close'].rolling(period).std()
        
        # Bollinger Bands
        df['bb_upper'] = df['sma'] + (multiplier * df['std'])
        df['bb_lower'] = df['sma'] - (multiplier * df['std'])
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        return df