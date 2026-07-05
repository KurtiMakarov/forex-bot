"""Metrics Calculator Module"""

import numpy as np


class MetricsCalculator:
    def calculate_sharpe_ratio(self, returns, risk_free_rate=0.0):
        """Calculate Sharpe Ratio"""
        # Convert to list or numpy array safely
        if returns is None:
            return 0.0

        returns_array = np.asarray(returns)

        if len(returns_array) < 2:
            return 0.0

        excess_returns = returns_array - risk_free_rate
        avg_excess_return = np.mean(excess_returns)
        std_dev = np.std(excess_returns)

        if std_dev == 0:
            return 0.0

        return avg_excess_return / std_dev

    def calculate_comprehensive_metrics(self, trades, initial_balance=10000):
        """Calculate full set of metrics for backtesting"""
        if not trades:
            return {
                'total_return': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0
            }

        profits = [t['profit_loss'] for t in trades]
        cumulative_profits = np.cumsum(profits)
        balance_history = initial_balance + cumulative_profits

        # Total Return
        total_return = (balance_history[-1] - initial_balance) / initial_balance * 100

        # Win Rate
        winning_trades = [p for p in profits if p > 0]
        losing_trades = [p for p in profits if p <= 0]
        win_rate = len(winning_trades) / len(trades) if trades else 0

        # Profit Factor
        gross_profit = sum(winning_trades) if winning_trades else 0
        gross_loss = abs(sum(losing_trades)) if losing_trades else 1  # Avoid div by zero
        profit_factor = gross_profit / gross_loss if gross_loss != 0 else 0

        # Max Drawdown
        peak = np.maximum.accumulate(balance_history)
        drawdown = (peak - balance_history) / peak
        max_drawdown = np.max(drawdown) * 100

        # Sharpe Ratio (Annualized approximation)
        # Calculate daily returns from balance history
        if len(balance_history) > 1:
            daily_returns = np.diff(balance_history) / balance_history[:-1]
            sharpe = self.calculate_sharpe_ratio(daily_returns) * np.sqrt(252)
        else:
            sharpe = 0.0

        return {
            'total_return': round(float(total_return), 2),
            'sharpe_ratio': round(float(sharpe), 2),
            'max_drawdown': round(float(max_drawdown), 2),
            'win_rate': round(float(win_rate), 2),
            'profit_factor': round(float(profit_factor), 2),
            'total_trades': len(trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades)
        }