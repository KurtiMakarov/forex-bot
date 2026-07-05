"""Risk Calculator - Position sizing for stocks with better diversification"""
from typing import Dict
from utils.logger import setup_logger
import math

logger = setup_logger('risk_calculator')


class RiskCalculator:
    def __init__(self):
        pass

    def _is_valid_number(self, value):
        """Check if value is a valid number"""
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

    def calculate_position_size(self, symbol: str, entry_price: float,
                                account_balance: float, atr_value: float = None) -> Dict:
        """Calculate position size for stocks"""

        # Validate entry_price
        if not self._is_valid_number(entry_price):
            logger.error(f"Invalid entry price for {symbol}: {entry_price}")
            return {'position_size': 0, 'risk_amount': 0, 'position_value': 0}

        # Only stocks allowed
        if not self._is_stock(symbol):
            logger.warning(f"Symbol {symbol} is not a stock. Skipping.")
            return {'position_size': 0, 'risk_amount': 0, 'position_value': 0}

        risk_per_trade = 0.02  # 2% risk per trade
        risk_amount = account_balance * risk_per_trade

        # ATR-based stop distance
        atr_valid = self._is_valid_number(atr_value)

        if atr_valid and atr_value > 0:
            # 🔥 ПО-АГРЕСИВЕН Stop Loss: ATR × 1.5 (беше × 2)
            stop_distance = atr_value * 1.5
            # Cap at 6% of price (беше 10%)
            max_stop = entry_price * 0.06
            stop_distance = min(stop_distance, max_stop)
            logger.info(f"📊 {symbol}: ATR-based Stop Loss: ${stop_distance:.2f}")
        else:
            # 🔥 Fallback: 3% of price (беше 5%)
            stop_distance = entry_price * 0.03
            logger.info(f"📊 {symbol}: Fixed % Stop Loss: ${stop_distance:.2f}")

        # Calculate shares
        if stop_distance > 0:
            position_size = risk_amount / stop_distance
        else:
            position_size = 1

        # Round down to whole shares
        position_size = max(1, int(position_size))

        # 🔥 ПО-МАЛКА позиция: 5% от баланса (беше 10%)
        max_position_value = account_balance * 0.05
        max_shares = int(max_position_value / entry_price)
        position_size = min(position_size, max(1, max_shares))

        position_value = position_size * entry_price

        logger.info(f"✅ {symbol}: {position_size} shares @ ${entry_price:.2f} = ${position_value:.2f}")

        return {
            'position_size': position_size,
            'risk_amount': risk_amount,
            'position_value': position_value
        }