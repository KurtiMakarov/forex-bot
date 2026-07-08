"""Paper Trader - Simulates trading for stocks with Trailing Stop"""
from datetime import datetime, timedelta
from typing import Dict, List
from utils.logger import setup_logger
import json
import os
import math

logger = setup_logger('paper_trader')

STATE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'state.json'
)


def safe_float(value, default=0.0):
    """Safely convert value to float"""
    if value is None:
        return default
    try:
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (TypeError, ValueError):
        return default


class PaperTrader:
    """Simulates a broker for stocks with Trailing Stop"""

    def __init__(self, initial_balance: float = 10000.0):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.positions = {}
        self.trades_history = []
        self.is_connected = True
        self.account_id = "PAPER-STOCKS-001"
        self.last_prices = {}
        self.notifier = None
        self._load_state()
        logger.info(f"Paper Trader initialized with ${self.balance:.2f}")

    def _get_notifier(self):
        """Lazy initialization of Telegram notifier"""
        if self.notifier is None:
            try:
                from utils.telegram_notifier import TelegramNotifier
                self.notifier = TelegramNotifier()
            except Exception as e:
                logger.warning(f"Could not initialize Telegram notifier: {e}")
        return self.notifier

    def _save_state(self):
        """Save state to JSON file"""
        try:
            state = {
                'balance': safe_float(self.balance, 0.0),
                'initial_balance': safe_float(self.initial_balance, 0.0),
                'account_id': self.account_id,
                'positions': self.positions,
                'trades_history': self.trades_history,
                'last_prices': {k: safe_float(v, 0.0) for k, v in self.last_prices.items()},
                'last_updated': datetime.now().isoformat()
            }
            with open(STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def _load_state(self):
        """Load previous state from JSON file"""
        if not os.path.exists(STATE_FILE):
            return
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                state = json.load(f)
            self.balance = safe_float(state.get('balance', self.initial_balance), self.initial_balance)
            self.positions = state.get('positions', {})
            self.trades_history = state.get('trades_history', [])
            self.last_prices = state.get('last_prices', {})
            logger.info(f"Loaded previous state: ${self.balance:.2f}, {len(self.positions)} positions")
        except Exception as e:
            logger.warning(f"Could not load state: {e}")

    def connect(self) -> bool:
        self.is_connected = True
        logger.info("Paper Trader connected")
        self._save_state()
        return True

    def disconnect(self):
        self.is_connected = False
        logger.info("Paper Trader disconnected")
        self._save_state()

    def get_balance(self) -> float:
        return safe_float(self.balance, 0.0)

    def update_balance(self) -> float:
        return self.get_balance()

    def set_price(self, symbol: str, price: float):
        """Set current price for a symbol"""
        self.last_prices[symbol] = safe_float(price, 0.0)
        self._save_state()

    def update_prices(self, prices: Dict[str, float]):
        """Update prices for multiple symbols"""
        self.last_prices.update({k: safe_float(v, 0.0) for k, v in prices.items()})
        self._save_state()

    def place_order(self, symbol: str, action: str, quantity: float,
                    sl_price: float = None, tp_price: float = None,
                    entry_price: float = None, atr_value: float = None) -> bool:
        """Place order for stocks with Trailing Stop setup"""
        try:
            quantity = safe_float(quantity, 0.0)
            sl_price = safe_float(sl_price, 0.0)
            tp_price = safe_float(tp_price, 0.0)
            entry_price = safe_float(entry_price, 0.0)

            if quantity <= 0:
                logger.error(f"Invalid quantity for {symbol}: {quantity}")
                return False

            if entry_price <= 0:
                entry_price = self.last_prices.get(symbol, 0.0)

            if entry_price <= 0:
                logger.error(f"Cannot get price for {symbol}")
                return False

            action = action.upper()
            position_value = quantity * entry_price
            margin_required = position_value

            logger.info(f"📈 Stock {symbol}: {quantity} shares × ${entry_price:.2f} = ${position_value:.2f}")

            if symbol in self.positions:
                existing = self.positions[symbol]
                if existing['action'] == action:
                    logger.info(f"Already have {action} position for {symbol}. Skipping.")
                    return True
                else:
                    opened_at = existing.get('opened_at', '')
                    if opened_at:
                        try:
                            opened_time = datetime.fromisoformat(opened_at)
                            time_held = datetime.now() - opened_time
                            if time_held < timedelta(hours=12):
                                logger.info(
                                    f"⏳ Position {symbol} held for {time_held.seconds // 3600}h "
                                    f"{(time_held.seconds // 60) % 60}m. Waiting 12h before closing."
                                )
                                return False
                        except Exception:
                            pass

                    logger.info(f"Closing opposite position for {symbol}")
                    self._close_position(symbol, entry_price, "Opposite signal")

            # Balance lock for BUY positions
            if action == 'BUY':
                if margin_required > self.balance:
                    logger.error(
                        f"Insufficient balance for {symbol}: need ${margin_required:.2f}, have ${self.balance:.2f}"
                    )
                    return False
                self.balance -= margin_required

            # Trailing stop setup
            if atr_value and safe_float(atr_value, 0.0) > 0:
                trailing_distance = safe_float(atr_value, 0.0) * 1.5
            else:
                trailing_distance = entry_price * 0.03

            if action == 'BUY':
                initial_trailing_stop = entry_price - trailing_distance
            else:
                initial_trailing_stop = entry_price + trailing_distance

            position = {
                'symbol': symbol,
                'action': action,
                'quantity': quantity,
                'entry_price': entry_price,
                'stop_loss': sl_price if sl_price > 0 else initial_trailing_stop,
                'take_profit': tp_price if tp_price > 0 else None,
                'margin_used': margin_required,
                'position_value': position_value,
                'is_forex': False,
                'opened_at': datetime.now().isoformat(),
                'status': 'OPEN',
                'trailing_enabled': True,
                'trailing_distance': trailing_distance,
                'highest_price': entry_price,
                'lowest_price': entry_price,
                'trailing_stop': initial_trailing_stop
            }

            self.positions[symbol] = position

            trade = {
                'id': len(self.trades_history) + 1,
                'symbol': symbol,
                'action': action,
                'quantity': quantity,
                'entry_price': entry_price,
                'stop_loss': position['stop_loss'],
                'take_profit': position['take_profit'],
                'margin_used': margin_required,
                'position_value': position_value,
                'is_forex': False,
                'timestamp': datetime.now().isoformat(),
                'status': 'OPEN',
                'pnl': 0.0
            }
            self.trades_history.append(trade)
            self._save_state()

            logger.info(f"📈 Paper Order: {action} {quantity} {symbol} @ ${entry_price:.2f}")
            logger.info(
                f"🎯 Trailing Stop enabled: distance=${trailing_distance:.2f}, initial SL=${initial_trailing_stop:.2f}"
            )
            logger.info(f"💵 Cost: ${margin_required:.2f}, Free balance: ${self.balance:.2f}")

            notifier = self._get_notifier()
            if notifier:
                try:
                    signal_data = {
                        'pair': symbol,
                        'action': action.lower(),
                        'entry_price': entry_price,
                        'stop_loss': position['stop_loss'],
                        'take_profit': position['take_profit'] if position['take_profit'] else 0,
                        'position_size': quantity,
                        'confidence': 0.75,
                        'reason': f'Signal executed (Trailing Stop: ${trailing_distance:.2f})'
                    }
                    notifier.send_trade_opened(signal_data)
                except Exception as e:
                    logger.warning(f"Could not send Telegram notification: {e}")

            return True

        except Exception as e:
            logger.error(f"Paper order error: {e}")
            return False

    def update_trailing_stops(self, current_prices: Dict[str, float]) -> List[tuple]:
        """Update trailing stops for open positions."""
        moved_stops = []

        for symbol, position in list(self.positions.items()):
            if symbol not in current_prices:
                continue
            if not position.get('trailing_enabled', False):
                continue

            current_price = safe_float(current_prices[symbol], 0.0)
            if current_price <= 0:
                continue

            action = position.get('action', 'BUY')
            trailing_distance = safe_float(position.get('trailing_distance', 0.0), 0.0)

            if action == 'BUY':
                highest_price = safe_float(position.get('highest_price', 0.0), 0.0)
                if current_price > highest_price:
                    position['highest_price'] = current_price
                    new_trailing_stop = current_price - trailing_distance
                    old_stop = safe_float(position.get('stop_loss', 0.0), 0.0)

                    if new_trailing_stop > old_stop:
                        position['stop_loss'] = new_trailing_stop
                        position['trailing_stop'] = new_trailing_stop
                        moved_stops.append((symbol, old_stop, new_trailing_stop))

            elif action == 'SELL':
                lowest_price = safe_float(position.get('lowest_price', float('inf')), float('inf'))
                if current_price < lowest_price:
                    position['lowest_price'] = current_price
                    new_trailing_stop = current_price + trailing_distance
                    old_stop = safe_float(position.get('stop_loss', 0.0), 0.0)

                    if old_stop == 0 or new_trailing_stop < old_stop:
                        position['stop_loss'] = new_trailing_stop
                        position['trailing_stop'] = new_trailing_stop
                        moved_stops.append((symbol, old_stop, new_trailing_stop))

        if moved_stops:
            self._save_state()

        return moved_stops

    def _close_position(self, symbol: str, exit_price: float, reason: str = "Manual close") -> float:
        """Close position and calculate P&L"""
        if symbol not in self.positions:
            return 0.0

        if exit_price <= 0:
            logger.error(f"❌ Cannot close {symbol} with invalid exit price: ${exit_price:.2f}")
            return 0.0

        position = self.positions[symbol]
        entry_price = safe_float(position['entry_price'], 0.0)
        quantity = safe_float(position['quantity'], 0.0)
        action = position['action']
        cost_basis = safe_float(position.get('margin_used', 0.0), 0.0)

        if action == 'BUY':
            pnl = (exit_price - entry_price) * quantity
            self.balance += cost_basis + pnl
        else:
            pnl = (entry_price - exit_price) * quantity
            self.balance += pnl

        for trade in reversed(self.trades_history):
            if trade['symbol'] == symbol and trade['status'] == 'OPEN':
                trade['status'] = 'CLOSED'
                trade['exit_price'] = safe_float(exit_price, 0.0)
                trade['closed_at'] = datetime.now().isoformat()
                trade['pnl'] = safe_float(pnl, 0.0)
                break

        del self.positions[symbol]
        self._save_state()

        pnl_emoji = "📈" if pnl >= 0 else "📉"
        logger.info(
            f"{pnl_emoji} Closed {symbol}: Exit ${exit_price:.2f}, P&L = ${pnl:.2f}, "
            f"Reason: {reason}, New balance: ${self.balance:.2f}"
        )

        notifier = self._get_notifier()
        if notifier:
            try:
                notifier.send_trade_closed(
                    symbol=symbol,
                    action=action,
                    entry_price=entry_price,
                    exit_price=exit_price,
                    quantity=quantity,
                    pnl=pnl,
                    reason=reason
                )
            except Exception as e:
                logger.warning(f"Could not send Telegram notification: {e}")

        return safe_float(pnl, 0.0)

    def get_positions(self) -> List[Dict]:
        """Get all open positions with current P&L"""
        result = []
        for symbol, position in self.positions.items():
            current_price = safe_float(self.last_prices.get(symbol, 0.0), 0.0)
            entry_price = safe_float(position.get('entry_price', 0.0), 0.0)
            quantity = safe_float(position.get('quantity', 0.0), 0.0)
            action = position.get('action', 'BUY')

            if current_price <= 0 or entry_price <= 0:
                unrealized_pnl = 0.0
            elif action == 'BUY':
                unrealized_pnl = (current_price - entry_price) * quantity
            else:
                unrealized_pnl = (entry_price - current_price) * quantity

            result.append({
                **position,
                'current_price': current_price,
                'unrealized_pnl': safe_float(unrealized_pnl, 0.0)
            })
        return result

    def get_trades_history(self, limit: int = 20) -> List[Dict]:
        """Get trades history"""
        return list(reversed(self.trades_history[-limit:]))

    def check_stop_loss_take_profit(self, current_prices: Dict[str, float]):
        """Check if any position hit SL or TP"""
        closed = []
        for symbol, position in list(self.positions.items()):
            if symbol not in current_prices:
                continue

            current_price = safe_float(current_prices[symbol], 0.0)
            if current_price <= 0:
                continue

            sl = safe_float(position.get('stop_loss', 0.0), 0.0)
            tp = safe_float(position.get('take_profit', 0.0), 0.0)
            action = position.get('action', 'BUY')

            if sl <= 0 and tp <= 0:
                continue

            if sl > 0:
                if action == 'BUY' and current_price <= sl:
                    pnl = self._close_position(symbol, current_price, "🛑 Stop Loss")
                    closed.append((symbol, 'STOP_LOSS', pnl))
                    continue
                elif action == 'SELL' and current_price >= sl:
                    pnl = self._close_position(symbol, current_price, "🛑 Stop Loss")
                    closed.append((symbol, 'STOP_LOSS', pnl))
                    continue

            if tp > 0:
                if action == 'BUY' and current_price >= tp:
                    pnl = self._close_position(symbol, current_price, "🎯 Take Profit")
                    closed.append((symbol, 'TAKE_PROFIT', pnl))
                elif action == 'SELL' and current_price <= tp:
                    pnl = self._close_position(symbol, current_price, "🎯 Take Profit")
                    closed.append((symbol, 'TAKE_PROFIT', pnl))

        return closed