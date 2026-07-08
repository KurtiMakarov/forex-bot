"""Risk Calculator - Position sizing for stocks with safer risk controls"""
from typing import Dict
from utils.logger import setup_logger
from utils.config import Config
import math

logger = setup_logger('risk_calculator')


class RiskCalculator:
    def __init__(self):
        self.config = Config()
        self.risk_per_trade = float(self.config.get('trading.risk_per_trade', 0.005))  # default 0.5%
        self.max_position_pct = float(self.config.get('trading.max_position_pct', 0.05))  # default 5%

    def _is_valid_number(self, value):
        """Check if value is a valid positive number"""
        if value is None:
            return False
        try:
            val = float(value)
            return not math.isnan(val) and not math.isinf(val) and val > 0
        except (TypeError, ValueError):
            return False

    def _is_stock(self, symbol: str) -> bool:
        """Check if symbol is a stock"""
        return '/' not in symbol and len(symbol) <= 5

    def calculate_position_size(
        self,
        symbol: str,
        entry_price: float,
        account_balance: float,
        atr_value: float = None
    ) -> Dict:
        """Calculate position size for stocks"""
        if not self._is_valid_number(entry_price):
            logger.error(f"Invalid entry price for {symbol}: {entry_price}")
            return {'position_size': 0, 'risk_amount': 0, 'position_value': 0}

        if not self._is_valid_number(account_balance):
            logger.error(f"Invalid account balance: {account_balance}")
            return {'position_size': 0, 'risk_amount': 0, 'position_value': 0}

        if not self._is_stock(symbol):
            logger.warning(f"Symbol {symbol} is not a stock. Skipping.")
            return {'position_size': 0, 'risk_amount': 0, 'position_value': 0}

        risk_amount = account_balance * self.risk_per_trade

        atr_valid = self._is_valid_number(atr_value)
        if atr_valid:
            stop_distance = float(atr_value) * 1.5
            max_stop = entry_price * 0.06
            stop_distance = min(stop_distance, max_stop)
            logger.info(f"📊 {symbol}: ATR-based stop distance: ${stop_distance:.2f}")
        else:
            stop_distance = entry_price * 0.03
            logger.info(f"📊 {symbol}: Fixed stop distance: ${stop_distance:.2f}")

        if stop_distance <= 0:
            return {'position_size': 0, 'risk_amount': 0, 'position_value': 0}

        position_size = int(risk_amount / stop_distance)
        position_size = max(1, position_size)

        max_position_value = account_balance * self.max_position_pct
        max_shares = int(max_position_value / entry_price)
        position_size = min(position_size, max(1, max_shares))

        position_value = position_size * entry_price

        logger.info(
            f"✅ {symbol}: size={position_size} shares, value=${position_value:.2f}, risk=${risk_amount:.2f}"
        )

        return {
            'position_size': position_size,
            'risk_amount': risk_amount,
            'position_value': position_value
        }