"""Performance tracking module"""

import pandas as pd
from datetime import datetime
from typing import Dict, List
from utils.logger import setup_logger

logger = setup_logger('performance_tracker')


class PerformanceTracker:
    """Tracks trading performance over time"""
    
    def __init__(self):
        self.trades = []
        self.equity_curve = []
        self.initial_balance = 10000
        self.current_balance = 10000
    
    def record_trade(self, trade: Dict):
        """Record a completed trade
        
        Args:
            trade: Trade details dictionary
        """
        trade_record = {
            'timestamp': datetime.now().isoformat(),
            'pair': trade.get('pair'),
            'action': trade.get('action'),
            'entry_price': trade.get('entry_price'),
            'exit_price': trade.get('exit_price'),
            'position_size': trade.get('position_size'),
            'profit_loss': trade.get('profit_loss', 0),
            'duration': trade.get('duration'),
            'strategy': trade.get('strategy'),
            'notes': trade.get('notes', '')
        }
        
        self.trades.append(trade_record)
        
        # Update equity curve
        self.current_balance += trade['profit_loss']
        self.equity_curve.append({
            'timestamp': trade_record['timestamp'],
            'balance': self.current_balance
        })
        
        logger.info(f"Trade recorded: P/L = {trade['profit_loss']:.2f}")
    
    def get_trade_history(self, pair: str = None, limit: int = None) -> List[Dict]:
        """Get trade history
        
        Args:
            pair: Filter by currency pair
            limit: Maximum number of trades to return
            
        Returns:
            List of trade records
        """
        trades = self.trades
        
        if pair:
            trades = [t for t in trades if t['pair'] == pair]
        
        if limit:
            trades = trades[-limit:]
        
        return trades
    
    def get_equity_curve(self) -> List[Dict]:
        """Get equity curve data"""
        return self.equity_curve
    
    def get_summary_statistics(self) -> Dict:
        """Get summary statistics"""
        if not self.trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_profit': 0,
                'total_loss': 0,
                'net_profit': 0,
                'current_balance': self.current_balance
            }
        
        winning_trades = [t for t in self.trades if t['profit_loss'] > 0]
        losing_trades = [t for t in self.trades if t['profit_loss'] <= 0]
        
        total_profit = sum(t['profit_loss'] for t in winning_trades)
        total_loss = sum(abs(t['profit_loss']) for t in losing_trades)
        
        return {
            'total_trades': len(self.trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': len(winning_trades) / len(self.trades) if self.trades else 0,
            'total_profit': total_profit,
            'total_loss': total_loss,
            'net_profit': self.current_balance - self.initial_balance,
            'current_balance': self.current_balance,
            'initial_balance': self.initial_balance,
            'return_percentage': ((self.current_balance - self.initial_balance) / self.initial_balance) * 100
        }
    
    def export_to_csv(self, filename: str = 'trade_history.csv'):
        """Export trade history to CSV"""
        if not self.trades:
            logger.warning("No trades to export")
            return
        
        df = pd.DataFrame(self.trades)
        df.to_csv(filename, index=False)
        logger.info(f"Trade history exported to {filename}")