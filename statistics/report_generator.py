"""Report generation module"""

import json
from datetime import datetime
from typing import Dict
from utils.logger import setup_logger
from .performance_tracker import PerformanceTracker
from .metrics_calculator import MetricsCalculator

logger = setup_logger('report_generator')


class ReportGenerator:
    """Generates trading performance reports"""
    
    def __init__(self, performance_tracker: PerformanceTracker):
        self.tracker = performance_tracker
        self.metrics_calculator = MetricsCalculator()
    
    def generate_daily_report(self) -> Dict:
        """Generate daily performance report"""
        summary = self.tracker.get_summary_statistics()
        trades_today = self._get_trades_for_period('today')
        
        report = {
            'report_type': 'daily',
            'generated_at': datetime.now().isoformat(),
            'summary': summary,
            'trades_today': len(trades_today),
            'profit_today': sum(t['profit_loss'] for t in trades_today),
            'recommendations': self._generate_recommendations(summary)
        }
        
        return report
    
    def generate_weekly_report(self) -> Dict:
        """Generate weekly performance report"""
        summary = self.tracker.get_summary_statistics()
        trades_week = self._get_trades_for_period('week')
        equity_curve = self.tracker.get_equity_curve()
        
        # Calculate metrics
        metrics = self.metrics_calculator.calculate_comprehensive_metrics(
            trades_week,
            equity_curve
        )
        
        report = {
            'report_type': 'weekly',
            'generated_at': datetime.now().isoformat(),
            'summary': summary,
            'metrics': metrics,
            'trades_this_week': len(trades_week),
            'recommendations': self._generate_recommendations(summary, metrics)
        }
        
        return report
    
    def generate_monthly_report(self) -> Dict:
        """Generate monthly performance report"""
        summary = self.tracker.get_summary_statistics()
        trades_month = self._get_trades_for_period('month')
        equity_curve = self.tracker.get_equity_curve()
        
        metrics = self.metrics_calculator.calculate_comprehensive_metrics(
            trades_month,
            equity_curve
        )
        
        report = {
            'report_type': 'monthly',
            'generated_at': datetime.now().isoformat(),
            'summary': summary,
            'metrics': metrics,
            'performance_by_pair': self._get_performance_by_pair(trades_month),
            'performance_by_strategy': self._get_performance_by_strategy(trades_month),
            'recommendations': self._generate_recommendations(summary, metrics)
        }
        
        return report
    
    def export_report(self, report: Dict, filename: str = None) -> str:
        """Export report to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"report_{report['report_type']}_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Report exported to {filename}")
        return filename
    
    def _get_trades_for_period(self, period: str):
        """Get trades for specified period"""
        # Simplified - in production would filter by date
        return self.tracker.get_trade_history(limit=100)
    
    def _get_performance_by_pair(self, trades):
        """Get performance breakdown by currency pair"""
        performance = {}
        
        for trade in trades:
            pair = trade.get('pair', 'Unknown')
            if pair not in performance:
                performance[pair] = {
                    'trades': 0,
                    'profit': 0,
                    'win_rate': 0,
                    'wins': 0
                }
            
            performance[pair]['trades'] += 1
            performance[pair]['profit'] += trade['profit_loss']
            
            if trade['profit_loss'] > 0:
                performance[pair]['wins'] += 1
        
        # Calculate win rates
        for pair in performance:
            if performance[pair]['trades'] > 0:
                performance[pair]['win_rate'] = performance[pair]['wins'] / performance[pair]['trades']
        
        return performance
    
    def _get_performance_by_strategy(self, trades):
        """Get performance breakdown by strategy"""
        performance = {}
        
        for trade in trades:
            strategy = trade.get('strategy', 'Unknown')
            if strategy not in performance:
                performance[strategy] = {
                    'trades': 0,
                    'profit': 0,
                    'win_rate': 0,
                    'wins': 0
                }
            
            performance[strategy]['trades'] += 1
            performance[strategy]['profit'] += trade['profit_loss']
            
            if trade['profit_loss'] > 0:
                performance[strategy]['wins'] += 1
        
        for strategy in performance:
            if performance[strategy]['trades'] > 0:
                performance[strategy]['win_rate'] = performance[strategy]['wins'] / performance[strategy]['trades']
        
        return performance
    
    def _generate_recommendations(self, summary, metrics=None):
        """Generate trading recommendations based on performance"""
        recommendations = []
        
        if summary.get('win_rate', 0) < 0.5:
            recommendations.append("Win rate is below 50%. Consider reviewing entry criteria.")
        
        if summary.get('net_profit', 0) < 0:
            recommendations.append("Overall performance is negative. Consider reducing position sizes.")
        
        if metrics:
            if metrics.get('sharpe_ratio', 0) < 1:
                recommendations.append("Sharpe ratio is low. Risk-adjusted returns need improvement.")
            
            if metrics.get('max_drawdown', 0) < -20:
                recommendations.append("Maximum drawdown exceeds 20%. Implement stricter risk management.")
        
        if not recommendations:
            recommendations.append("Performance is satisfactory. Continue current strategy.")
        
        return recommendations