"""Correlation Matrix Module"""

import pandas as pd
import numpy as np
from data_collector.market_data import MarketDataCollector
from utils.logger import setup_logger

logger = setup_logger('correlation_matrix')

class CorrelationMatrix:
    def __init__(self):
        self.market_data = MarketDataCollector()
        self.pairs = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD", "NZD/USD", "USD/CHF"]
    
    def get_correlation_data(self, days=30):
        """Calculate correlation between all major pairs"""
        logger.info("Calculating correlation matrix...")
        
        # 1. Събираме данни за всички двойки
        price_data = {}
        for pair in self.pairs:
            df = self.market_data.get_historical_data(pair, days=days)
            if not df.empty:
                # Използваме процентната промяна (returns), а не цената, за по-точна корелация
                price_data[pair] = df['close'].pct_change().dropna()
        
        if not price_data:
            return pd.DataFrame()
            
        # 2. Обединяваме данните в една таблица
        combined_df = pd.DataFrame(price_data)
        
        # 3. Изчисляваме корелацията
        corr_matrix = combined_df.corr()
        
        return corr_matrix

    def get_highly_correlated_pairs(self, threshold=0.8):
        """Find pairs that move very similarly"""
        matrix = self.get_correlation_data()
        if matrix.empty:
            return []
            
        highly_correlated = []
        pairs = matrix.columns
        
        for i in range(len(pairs)):
            for j in range(i + 1, len(pairs)):
                pair1 = pairs[i]
                pair2 = pairs[j]
                corr_value = matrix.loc[pair1, pair2]
                
                if abs(corr_value) >= threshold:
                    highly_correlated.append({
                        'pair_1': pair1,
                        'pair_2': pair2,
                        'correlation': round(corr_value, 2),
                        'type': 'Positive' if corr_value > 0 else 'Negative'
                    })
                    
        return highly_correlated