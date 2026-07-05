"""Strategy Optimization Module"""

import itertools
from utils.logger import setup_logger
from strategies.trend_following import TrendFollowingStrategy
from strategies.mean_reversion import MeanReversionStrategy
from data_collector.market_data import MarketDataCollector
from statistics.metrics_calculator import MetricsCalculator

logger = setup_logger('optimizer')


class StrategyOptimizer:
    def __init__(self):
        self.market_data = MarketDataCollector()
        self.metrics_calc = MetricsCalculator()

    def optimize_trend_following(self, pair, days=365):
        """Optimize Trend Following Strategy parameters"""
        logger.info(f"Optimizing Trend Following for {pair}...")

        short_ma_range = [10, 20, 30]
        long_ma_range = [50, 100, 200]

        # Default result structure to prevent KeyError
        best_result = {'sharpe': -999, 'params': {}, 'net_profit': 0, 'total_trades': 0}
        data = self.market_data.get_historical_data(pair, days=days)

        if data.empty:
            return best_result

        for short_ma, long_ma in itertools.product(short_ma_range, long_ma_range):
            if short_ma >= long_ma: continue

            strategy = TrendFollowingStrategy(parameters={'short_ma': short_ma, 'long_ma': long_ma})
            trades = self._simulate_strategy(strategy, data)

            if trades:
                profits = [t['profit_loss'] for t in trades]
                sharpe = self.metrics_calc.calculate_sharpe_ratio([p / 10000 for p in profits])

                if sharpe > best_result['sharpe']:
                    best_result = {
                        'sharpe': sharpe,
                        'params': {'short_ma': short_ma, 'long_ma': long_ma},
                        'total_trades': len(trades),
                        'net_profit': sum(profits)
                    }

        return best_result

    def optimize_mean_reversion(self, pair, days=365):
        """Optimize Mean Reversion Strategy parameters"""
        logger.info(f"Optimizing Mean Reversion for {pair}...")

        rsi_period_range = [7, 14, 21]
        std_dev_range = [1.5, 2.0, 2.5]

        best_result = {'sharpe': -999, 'params': {}, 'net_profit': 0, 'total_trades': 0}
        data = self.market_data.get_historical_data(pair, days=days)

        if data.empty:
            return best_result

        for rsi_p, std_d in itertools.product(rsi_period_range, std_dev_range):
            strategy = MeanReversionStrategy(parameters={
                'lookback_period': 20,
                'std_dev_multiplier': std_d,
                'rsi_overbought': 70,
                'rsi_oversold': 30
            })

            trades = self._simulate_strategy(strategy, data)

            if trades:
                profits = [t['profit_loss'] for t in trades]
                sharpe = self.metrics_calc.calculate_sharpe_ratio([p / 10000 for p in profits])

                if sharpe > best_result['sharpe']:
                    best_result = {
                        'sharpe': sharpe,
                        'params': {'std_dev': std_d, 'rsi_period': rsi_p},
                        'total_trades': len(trades),
                        'net_profit': sum(profits)
                    }

        return best_result

    def _simulate_strategy(self, strategy, data):
        """Simple simulation for optimization speed"""
        trades = []
        position = None

        for i in range(50, len(data)):
            current_data = data.iloc[:i + 1]
            current_price = data['close'].iloc[i]

            signal = strategy.generate_signal(current_data, current_price)

            if signal['action'] == 'buy' and position is None:
                position = {'type': 'long', 'entry': current_price}
            elif signal['action'] == 'sell' and position is None:
                position = {'type': 'short', 'entry': current_price}

            elif position:
                exit_price = current_price
                close_trade = False

                if position['type'] == 'long':
                    if signal['action'] == 'sell' or exit_price < position['entry'] * 0.98 or exit_price > position[
                        'entry'] * 1.04:
                        close_trade = True
                else:
                    if signal['action'] == 'buy' or exit_price > position['entry'] * 1.02 or exit_price < position[
                        'entry'] * 0.96:
                        close_trade = True

                if close_trade:
                    profit = (exit_price - position['entry']) * 100000 if position['type'] == 'long' else (position[
                                                                                                               'entry'] - exit_price) * 100000
                    trades.append({'profit_loss': profit})
                    position = None

        return trades