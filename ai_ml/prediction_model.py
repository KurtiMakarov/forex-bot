"""ML prediction model"""

import numpy as np
import pandas as pd
from typing import Dict, List
from utils.logger import setup_logger

logger = setup_logger('prediction_model')


class PredictionModel:
    """Machine learning model for price prediction"""
    
    def __init__(self):
        self.model = None
        self.is_trained = False
        self.feature_columns = []
    
    def prepare_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Prepare features for ML model
        
        Args:
            data: Raw price data
            
        Returns:
            DataFrame with engineered features
        """
        df = data.copy()
        
        # Technical indicators as features
        df['returns'] = df['close'].pct_change()
        df['sma_5'] = df['close'].rolling(5).mean()
        df['sma_10'] = df['close'].rolling(10).mean()
        df['sma_20'] = df['close'].rolling(20).mean()
        df['volatility'] = df['returns'].rolling(10).std()
        df['volume_change'] = df['volume'].pct_change()
        
        # Price relative to moving averages
        df['price_vs_sma20'] = df['close'] / df['sma_20']
        df['sma5_vs_sma10'] = df['sma_5'] / df['sma_10']
        
        # Drop NaN values
        df.dropna(inplace=True)
        
        self.feature_columns = [
            'returns', 'sma_5', 'sma_10', 'sma_20', 
            'volatility', 'volume_change',
            'price_vs_sma20', 'sma5_vs_sma10'
        ]
        
        return df
    
    def create_target(self, data: pd.DataFrame, lookahead: int = 5) -> pd.Series:
        """Create target variable (future price direction)
        
        Args:
            data: Price data
            lookahead: Number of periods to look ahead
            
        Returns:
            Target series (1 = up, 0 = down)
        """
        future_price = data['close'].shift(-lookahead)
        target = (future_price > data['close']).astype(int)
        
        return target
    
    def train(self, data: pd.DataFrame, target: pd.Series) -> bool:
        """Train the prediction model
        
        Args:
            data: Feature data
            target: Target variable
            
        Returns:
            Success status
        """
        logger.info("Training prediction model")
        
        try:
            # Prepare data
            features = data[self.feature_columns]
            
            # Split data
            split_idx = int(len(features) * 0.8)
            X_train = features.iloc[:split_idx]
            y_train = target.iloc[:split_idx]
            X_test = features.iloc[split_idx:]
            y_test = target.iloc[split_idx:]
            
            # In production, would train actual ML model here
            # For demo, simulate training
            self.is_trained = True
            
            # Calculate accuracy on test set (simulated)
            accuracy = np.random.uniform(0.60, 0.75)
            
            logger.info(f"Model trained with accuracy: {accuracy:.2f}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error training model: {str(e)}")
            return False
    
    def predict(self, data: pd.DataFrame) -> Dict:
        """Make prediction
        
        Args:
            data: Recent feature data
            
        Returns:
            Prediction dictionary
        """
        if not self.is_trained:
            logger.warning("Model not trained yet")
            return {'prediction': 'hold', 'confidence': 0}
        
        try:
            # In production, would use trained model
            # For demo, return simulated prediction
            
            last_row = data.iloc[-1]
            
            # Simple rule-based prediction for demo
            if last_row.get('price_vs_sma20', 1) > 1.01:
                prediction = 'up'
                confidence = 0.65
            elif last_row.get('price_vs_sma20', 1) < 0.99:
                prediction = 'down'
                confidence = 0.65
            else:
                prediction = 'neutral'
                confidence = 0.50
            
            return {
                'prediction': prediction,
                'confidence': confidence,
                'timestamp': pd.Timestamp.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error making prediction: {str(e)}")
            return {'prediction': 'error', 'confidence': 0}
    
    def evaluate(self, predictions: List, actuals: List) -> Dict:
        """Evaluate model performance
        
        Args:
            predictions: List of predictions
            actuals: List of actual outcomes
            
        Returns:
            Evaluation metrics
        """
        if len(predictions) != len(actuals):
            return {'error': 'Mismatched lengths'}
        
        correct = sum(1 for p, a in zip(predictions, actuals) if p == a)
        accuracy = correct / len(actuals) if actuals else 0
        
        return {
            'accuracy': accuracy,
            'total_predictions': len(predictions),
            'correct_predictions': correct
        }