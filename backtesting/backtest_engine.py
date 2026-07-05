"""Backtest Engine Module"""

import pandas as pd
from datetime import datetime
from utils.logger import setup_logger
from data_collector.market_data import MarketDataCollector
from strategies.strategy_manager import StrategyManager
from statistics.metrics_calculator import MetricsCalculator

logger = setup_logger('backtest_engine')

class BacktestEngine:
    def __init__(self):
        self.market_data = MarketDataCollector()
        self.strategy_manager = StrategyManager()
        self.metrics_calculator = MetricsCalculator()

    def run_backtest(self, pair, days=365, initial_balance=10000):
        """Run backtest on historical data"""
        logger.info(f"Running backtest for {pair} over {days} days")

        data = self.market_data.get_historical_data(pair, days=days)
        if data.empty:
            return {'error': 'No data available', 'trades': [], 'summary': {}}

        trades = []
        position = None
        balance = initial_balance

        # Iterate through data
        for i in range(50, len(data)):
            current_data = data.iloc[:i+1]
            current_price = data['close'].iloc[i]
            current_date = data.index[i]

            # Get signal from strategy manager
            signal = self.strategy_manager.get_combined_signal(current_data, current_price)

            # Entry Logic
            if position is None and signal['action'] != 'hold':
                position = {
                    'type': signal['action'], # 'buy' or 'sell'
                    'entry_price': current_price,
                    'entry_date': current_date,
                    'size': 1.0 # Standard lot for simplicity
                }

            # Exit Logic
            elif position is not None:
                close_trade = False
                exit_price = current_price

                # Simple exit: opposite signal or fixed SL/TP logic could be added here
                if signal['action'] == 'hold':
                    # For backtesting, let's use a simple time-based or opposite signal exit
                    # Or check if price hit a hypothetical SL/TP based on entry
                    entry_p = position['entry_price']
                    if position['type'] == 'buy':
                        if current_price < entry_p * 0.98 or current_price > entry_p * 1.04: # 2% SL, 4% TP
                            close_trade = True
                    else:
                        if current_price > entry_p * 1.02 or current_price < entry_p * 0.96:
                            close_trade = True

                if signal['action'] != position['type']: # Close on opposite signal
                     close_trade = True

                if close_trade:
                    # Calculate P/L
                    if position['type'] == 'buy':
                        profit = (exit_price - position['entry_price']) * position['size'] * 100000
                    else:
                        profit = (position['entry_price'] - exit_price) * position['size'] * 100000

                    trade_record = {
                        'pair': pair,
                        'action': position['type'],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'entry_date': position['entry_date'],
                        'exit_date': current_date,
                        'profit_loss': profit,
                        'strategy': 'Combined_AI'
                    }

                    trades.append(trade_record)
                    balance += profit
                    position = None

        # Calculate Metrics
        summary = self.metrics_calculator.calculate_comprehensive_metrics(trades, initial_balance)

        return {
            'trades': trades,
            'summary': summary,
            'final_balance': balance,
            'total_return': summary['total_return']
        }