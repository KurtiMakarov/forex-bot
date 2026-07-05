"""Position sizing module"""

from utils.logger import setup_logger
from utils.config import Config

logger = setup_logger('position_sizer')


class PositionSizer:
    """Calculates optimal position sizes based on risk management rules"""
    
    def __init__(self):
        self.config = Config()
        self.trading_config = self.config.trading_config
    
    def calculate_kelly_position_size(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        """Calculate position size using Kelly Criterion
        
        Args:
            win_rate: Win rate (0-1)
            avg_win: Average winning trade amount
            avg_loss: Average losing trade amount
            
        Returns:
            Optimal position size fraction (0-1)
        """
        if avg_loss == 0:
            return 0
        
        # Kelly formula: f = (p * b - q) / b
        # where p = win probability, q = loss probability, b = win/loss ratio
        p = win_rate
        q = 1 - win_rate
        b = avg_win / avg_loss if avg_loss != 0 else 0
        
        kelly_fraction = (p * b - q) / b
        
        # Use half-Kelly for more conservative sizing
        conservative_kelly = kelly_fraction / 2
        
        # Clamp between 0 and max position size
        max_position = self.trading_config.get('max_position_size', 10000)
        return max(0, min(conservative_kelly, 1.0))
    
    def calculate_fixed_fraction_size(self, account_balance: float, risk_per_trade: float = None) -> float:
        """Calculate position size using fixed fraction method
        
        Args:
            account_balance: Total account balance
            risk_per_trade: Risk percentage per trade
            
        Returns:
            Dollar amount to risk
        """
        if risk_per_trade is None:
            risk_per_trade = self.trading_config.get('risk_per_trade', 0.02)
        
        return account_balance * risk_per_trade
    
    def calculate_volatility_adjusted_size(self, atr: float, account_balance: float) -> float:
        """Calculate position size adjusted for volatility
        
        Args:
            atr: Average True Range
            account_balance: Account balance
            
        Returns:
            Position size in units
        """
        risk_amount = account_balance * self.trading_config.get('risk_per_trade', 0.02)
        
        if atr == 0:
            return 0
        
        # Position size = Risk Amount / (ATR * Multiplier)
        position_size = risk_amount / (atr * 2)
        
        return position_size
    
    def apply_maximum_drawdown_limit(self, position_size: float, current_drawdown: float) -> float:
        """Apply maximum drawdown limit
        
        Args:
            position_size: Calculated position size
            current_drawdown: Current drawdown percentage
            
        Returns:
            Adjusted position size
        """
        max_daily_loss = self.trading_config.get('max_daily_loss', 0.05)
        
        if current_drawdown >= max_daily_loss:
            logger.warning("Maximum daily loss reached. Reducing position size to 0.")
            return 0
        
        # Reduce position size as drawdown increases
        reduction_factor = 1 - (current_drawdown / max_daily_loss)
        return position_size * max(0, reduction_factor)