"""Breakout Strategy Module"""

import pandas as pd
from utils.logger import setup_logger

logger = setup_logger('breakout_strategy')

class BreakoutStrategy:
    def __init__(self, parameters=None):
        self.parameters = parameters or {'lookback': 20}
        self.lookback = self.parameters.get('lookback', 20)

    def generate_signal(self, data, current_price):
        """Generate signal based on Donchian Channel Breakout"""
        if len(data) < self.lookback:
            return {'action': 'hold', 'confidence': 0, 'reason': 'Not enough data'}

        highs = data['high'].rolling(window=self.lookback).max()
        lows = data['low'].rolling(window=self.lookback).min()

        prev_high = highs.iloc[-2]
        prev_low = lows.iloc[-2]

        action = 'hold'
        confidence = 0.6
        reason = ""

        if current_price > prev_high:
            action = 'buy'
            confidence = 0.75
            reason = f"Probiv na gornata granica ({self.lookback}-period)"
        elif current_price < prev_low:
            action = 'sell'
            confidence = 0.75
            reason = f"Probiv na dolnata granica ({self.lookback}-period)"

        return {'action': action, 'confidence': confidence, 'reason': reason}