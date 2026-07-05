"""Signal Engine - Generates trading signals for stocks with RSI filter"""
import pandas as pd
import numpy as np
import math
from datetime import datetime
from typing import Dict, Optional
from utils.logger import setup_logger
from utils.config import Config
from data_collector.market_data import MarketDataCollector
from data_collector.news import NewsCollector
from strategies.strategy_manager import StrategyManager
from risk_management.risk_calculator import RiskCalculator
from utils.telegram_notifier import TelegramNotifier
from broker.paper_trader import PaperTrader
from broker.ib_connector import IBConnector
from data_collector.economic_calendar import EconomicCalendar

logger = setup_logger('signal_engine')


class SignalEngine:
    """Generates and manages trading signals"""

    def __init__(self):
        self.config = Config()
        self.market_data = MarketDataCollector()
        self.news_collector = NewsCollector()
        self.strategy_manager = StrategyManager()
        self.risk_calculator = RiskCalculator()
        self.notifier = TelegramNotifier()
        self.calendar = EconomicCalendar()

        broker_type = self.config.get('broker.type', 'paper_trader')

        if broker_type == 'interactive_brokers':
            logger.info("Initializing Interactive Brokers Connector...")
            self.broker = IBConnector()
        else:
            logger.info("Initializing Paper Trader...")
            self.broker = PaperTrader(initial_balance=10000)

        self.active_signals = {}

    def _is_stock(self, symbol: str) -> bool:
        """Check if symbol is a stock"""
        return '/' not in symbol and len(symbol) <= 5

    def _is_valid_number(self, value):
        """Check if value is a valid number"""
        if value is None:
            return False
        try:
            val = float(value)
            return not math.isnan(val) and not math.isinf(val)
        except (TypeError, ValueError):
            return False

    def _get_last_valid_price(self, historical_data: pd.DataFrame) -> Optional[float]:
        """Get the last valid (non-NaN) price"""
        try:
            valid_prices = historical_data['close'].dropna()
            if valid_prices.empty:
                return None
            return float(valid_prices.iloc[-1])
        except Exception as e:
            logger.warning(f"Could not get last valid price: {e}")
            return None

    def _calculate_atr(self, historical_data: pd.DataFrame, period: int = 14) -> Optional[float]:
        """Calculate ATR from historical data"""
        try:
            df = historical_data.dropna(subset=['high', 'low', 'close'])

            if len(df) < period + 1:
                return None

            high = df['high']
            low = df['low']
            close = df['close']
            prev_close = close.shift(1)

            tr1 = high - low
            tr2 = abs(high - prev_close)
            tr3 = abs(low - prev_close)

            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = true_range.rolling(window=period).mean().iloc[-1]

            if pd.isna(atr):
                return None

            return float(atr)
        except Exception as e:
            logger.warning(f"ATR calculation failed: {e}")
            return None

    def _calculate_rsi(self, historical_data: pd.DataFrame, period: int = 14) -> Optional[float]:
        """Calculate RSI from historical data"""
        try:
            df = historical_data.dropna(subset=['close'])

            if len(df) < period + 1:
                return None

            close = df['close']
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            rsi_value = rsi.iloc[-1]

            if pd.isna(rsi_value):
                return None

            return float(rsi_value)
        except Exception as e:
            logger.warning(f"RSI calculation failed: {e}")
            return None

    def generate_signal(self, symbol: str, force_test_mode: bool = False) -> Dict:
        """Generate trading signal for a stock"""
        logger.info(f"Generating signal for {symbol}")

        try:
            historical_data = self.market_data.get_historical_data(symbol, days=100)
            if historical_data.empty:
                return {
                    'pair': symbol, 'timestamp': datetime.now().isoformat(),
                    'action': 'hold', 'confidence': 0, 'entry_price': 0.0,
                    'stop_loss': 0.0, 'take_profit': 0.0,
                    'position_size': 0.0, 'reason': 'No data',
                    'rsi': None, 'atr': None
                }

            current_price = self._get_last_valid_price(historical_data)

            if not self._is_valid_number(current_price):
                logger.error(f"Current price is invalid for {symbol}")
                return {
                    'pair': symbol, 'timestamp': datetime.now().isoformat(),
                    'action': 'hold', 'confidence': 0, 'entry_price': 0.0,
                    'stop_loss': 0.0, 'take_profit': 0.0,
                    'position_size': 0.0, 'reason': 'Invalid price data',
                    'rsi': None, 'atr': None
                }

            logger.info(f"Current price for {symbol}: ${current_price:.2f}")

            # Изчисляване на RSI и ATR
            rsi_value = self._calculate_rsi(historical_data, period=14)
            atr_value = self._calculate_atr(historical_data, period=14)

            if rsi_value and not pd.isna(rsi_value):
                logger.info(f"RSI for {symbol}: {rsi_value:.1f}")
            else:
                rsi_value = None

            if atr_value and not pd.isna(atr_value):
                logger.info(f"ATR for {symbol}: ${atr_value:.2f}")
            else:
                atr_value = None

            if force_test_mode:
                is_buy = np.random.rand() > 0.5
                final_action = 'buy' if is_buy else 'sell'
                confidence = 0.85
                reason = "SIMULATION: Test Mode"
                stop_loss = current_price * 0.95 if is_buy else current_price * 1.05
                take_profit = current_price * 1.10 if is_buy else current_price * 0.90
            else:
                strategy_signal = self.strategy_manager.get_combined_signal(historical_data, current_price)

                news = self.news_collector.get_market_news(keywords=[symbol], limit=3)
                sentiment_score = 0
                for item in news:
                    sentiment = self.news_collector.analyze_sentiment(item.get('summary', ''))
                    sentiment_score += sentiment['score']

                avg_sentiment = sentiment_score / len(news) if news else 0

                final_action = strategy_signal['action']
                confidence = strategy_signal['confidence']
                reason = strategy_signal['reason']

                if avg_sentiment > 0.5 and final_action != 'buy':
                    final_action = 'buy'
                    confidence = max(confidence, 0.75)
                    reason += " | Positive news"
                elif avg_sentiment < -0.5 and final_action != 'sell':
                    final_action = 'sell'
                    confidence = max(confidence, 0.75)
                    reason += " | Negative news"

                # RSI ФИЛТЪР (по-строги прагове)
                if rsi_value is not None:
                    if final_action == 'buy' and rsi_value > 65:
                        logger.warning(f"RSI FILTER: {symbol} RSI={rsi_value:.1f} > 65 (overbought). Changing BUY to HOLD")
                        final_action = 'hold'
                        confidence = 0.3
                        reason = f"RSI overbought ({rsi_value:.1f} > 65). Waiting for pullback."
                    elif final_action == 'sell' and rsi_value < 35:
                        logger.warning(f"RSI FILTER: {symbol} RSI={rsi_value:.1f} < 35 (oversold). Changing SELL to HOLD")
                        final_action = 'hold'
                        confidence = 0.3
                        reason = f"RSI oversold ({rsi_value:.1f} < 35). Waiting for bounce."

                # Изчисляване на Stop Loss и Take Profit
                if atr_value and not pd.isna(atr_value):
                    sl_dist = atr_value * 3.0
                    tp_dist = atr_value * 6.0
                    stop_loss = current_price - sl_dist if final_action == 'buy' else current_price + sl_dist
                    take_profit = current_price + tp_dist if final_action == 'buy' else current_price - tp_dist
                else:
                    if final_action == 'buy':
                        stop_loss = current_price * 0.95
                        take_profit = current_price * 1.10
                    elif final_action == 'sell':
                        stop_loss = current_price * 1.05
                        take_profit = current_price * 0.90
                    else:
                        stop_loss = 0.0
                        take_profit = 0.0

            account_balance = 10000
            if hasattr(self.broker, 'get_balance'):
                bal = self.broker.get_balance()
                if bal > 0:
                    account_balance = bal

            risk_params = self.risk_calculator.calculate_position_size(
                symbol=symbol,
                entry_price=current_price,
                account_balance=account_balance,
                atr_value=atr_value
            )

            position_size = risk_params.get('position_size', 0.0)

            if not self._is_valid_number(stop_loss):
                stop_loss = 0.0
            if not self._is_valid_number(take_profit):
                take_profit = 0.0
            if not self._is_valid_number(position_size):
                position_size = 0.0

            signal = {
                'pair': symbol,
                'timestamp': datetime.now().isoformat(),
                'action': final_action,
                'confidence': confidence,
                'entry_price': float(current_price),
                'stop_loss': float(stop_loss),
                'take_profit': float(take_profit),
                'position_size': float(position_size),
                'reason': reason,
                'rsi': float(rsi_value) if rsi_value else None,
                'atr': float(atr_value) if atr_value else None
            }

            self.active_signals[symbol] = signal

            return signal

        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return {
                'pair': symbol, 'timestamp': datetime.now().isoformat(),
                'action': 'hold', 'confidence': 0, 'entry_price': 0.0,
                'stop_loss': 0.0, 'take_profit': 0.0,
                'position_size': 0.0, 'reason': f'Error: {str(e)}',
                'rsi': None, 'atr': None
            }

    def scan_market(self, symbols: Optional[list] = None) -> list:
        """Scan multiple symbols for signals"""
        if symbols is None:
            symbols = self.config.get('data.supported_pairs', ['AAPL'])

        signals = []
        for symbol in symbols:
            signal = self.generate_signal(symbol)
            signals.append(signal)

        signals.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        return signals

    def get_active_signals(self) -> Dict:
        """Get all active signals"""
        return self.active_signals