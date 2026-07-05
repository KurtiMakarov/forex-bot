"""Autonomous Trading Bot Runner - Stocks with safety guardrails + journaling + live readiness gate"""
import time
import sys
import os
import signal
import json
from datetime import datetime, date, timedelta
import pytz

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from signal_generator.signal_engine import SignalEngine
from utils.logger import setup_logger
from utils.config import Config
from utils.live_readiness import evaluate_live_readiness

logger = setup_logger('bot_runner')


def nth_weekday_of_month(year: int, month: int, weekday: int, n: int) -> date:
    d = date(year, month, 1)
    shift = (weekday - d.weekday()) % 7
    d = d + timedelta(days=shift)
    d = d + timedelta(weeks=n - 1)
    return d


def last_weekday_of_month(year: int, month: int, weekday: int) -> date:
    if month == 12:
        d = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        d = date(year, month + 1, 1) - timedelta(days=1)
    shift = (d.weekday() - weekday) % 7
    return d - timedelta(days=shift)


def observed_us_holiday(d: date) -> date:
    if d.weekday() == 5:
        return d - timedelta(days=1)
    if d.weekday() == 6:
        return d + timedelta(days=1)
    return d


def easter_sunday(year: int) -> date:
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def nyse_holidays(year: int) -> set[date]:
    holidays = set()
    holidays.add(observed_us_holiday(date(year, 1, 1)))
    holidays.add(observed_us_holiday(date(year, 6, 19)))
    holidays.add(observed_us_holiday(date(year, 7, 4)))
    holidays.add(observed_us_holiday(date(year, 12, 25)))
    holidays.add(nth_weekday_of_month(year, 1, 0, 3))
    holidays.add(nth_weekday_of_month(year, 2, 0, 3))
    holidays.add(last_weekday_of_month(year, 5, 0))
    holidays.add(nth_weekday_of_month(year, 9, 0, 1))
    holidays.add(nth_weekday_of_month(year, 11, 3, 4))
    holidays.add(easter_sunday(year) - timedelta(days=2))
    return holidays


def is_us_market_open(include_holidays: bool = True) -> bool:
    ny = pytz.timezone("America/New_York")
    now = datetime.now(ny)
    today = now.date()

    if now.weekday() >= 5:
        return False

    if include_holidays and today in nyse_holidays(today.year):
        return False

    market_open = datetime.strptime("09:30", "%H:%M").time()
    market_close = datetime.strptime("16:00", "%H:%M").time()
    return market_open <= now.time() <= market_close


class TradingBot:
    def __init__(self):
        self.config = Config()
        self.config.set('broker.ib_client_id', 1)

        self.engine = SignalEngine()
        self.is_running = False
        self.scan_interval = int(self.config.get('trading.scan_interval_seconds', 60))

        self.symbols = self.config.get('data.supported_pairs', ['AAPL'])

        self.broker_mode = str(self.config.get('broker.mode', 'paper')).lower()
        self.allow_live = bool(self.config.get('broker.allow_live_trading', False))

        self.max_daily_loss = float(self.config.get('trading.max_daily_loss', 0.01))
        self.kill_switch_on_daily_loss = bool(self.config.get('trading.kill_switch_on_daily_loss', True))
        self.max_open_positions = int(self.config.get('trading.max_open_positions', 3))
        self.block_orders_when_market_closed = bool(
            self.config.get('trading.block_orders_when_market_closed', True)
        )

        self.journal_path = self.config.get('trading.journal_path', 'journal/trades.jsonl')
        os.makedirs(os.path.dirname(self.journal_path), exist_ok=True)

        # LIVE READINESS GATE
        self.live_gate_enabled = bool(self.config.get('trading.live_readiness.enabled', True))
        self.live_gate_min_closed_trades = int(self.config.get('trading.live_readiness.min_closed_trades', 30))
        self.live_gate_lookback_days = int(self.config.get('trading.live_readiness.lookback_days', 30))
        self.live_gate_min_profit_factor = float(self.config.get('trading.live_readiness.min_profit_factor', 1.20))
        self.live_gate_max_drawdown = float(self.config.get('trading.live_readiness.max_drawdown', 0.05))
        self.live_gate_min_win_rate = float(self.config.get('trading.live_readiness.min_win_rate', 0.40))
        self.live_unlocked = False

        self.day_start_balance = None

        signal.signal(signal.SIGINT, self.stop_bot)
        signal.signal(signal.SIGTERM, self.stop_bot)

    def _journal(self, event_type: str, payload: dict):
        record = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "event_type": event_type,
            "broker_mode": self.broker_mode,
            **payload
        }
        try:
            with open(self.journal_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Failed to write journal entry: {e}")

    def _is_daily_loss_exceeded(self, current_balance: float) -> bool:
        if self.day_start_balance is None:
            self.day_start_balance = current_balance
            return False

        if self.day_start_balance <= 0:
            return False

        daily_drawdown = (self.day_start_balance - current_balance) / self.day_start_balance
        if daily_drawdown >= self.max_daily_loss:
            logger.error(f"🛑 Daily loss limit hit: {daily_drawdown:.2%} >= {self.max_daily_loss:.2%}")
            self._journal("risk_halt", {
                "reason": "daily_loss_limit",
                "daily_drawdown": daily_drawdown,
                "max_daily_loss": self.max_daily_loss,
                "current_balance": current_balance,
                "day_start_balance": self.day_start_balance
            })
            return True
        return False

    def _open_positions_count(self) -> int:
        broker = self.engine.broker
        if hasattr(broker, 'get_positions'):
            try:
                return len(broker.get_positions() or [])
            except Exception:
                return 0
        return 0

    def _evaluate_live_gate(self):
        if self.broker_mode != "live":
            self.live_unlocked = True
            return

        if not self.live_gate_enabled:
            self.live_unlocked = bool(self.allow_live)
            return

        result = evaluate_live_readiness(
            journal_path=self.journal_path,
            min_closed_trades=self.live_gate_min_closed_trades,
            lookback_days=self.live_gate_lookback_days,
            min_profit_factor=self.live_gate_min_profit_factor,
            max_drawdown_limit=self.live_gate_max_drawdown,
            min_win_rate=self.live_gate_min_win_rate,
        )

        self.live_unlocked = bool(self.allow_live and result.ready)

        logger.info(
            f"🔐 Live readiness: ready={result.ready} | unlocked={self.live_unlocked} | "
            f"reason={result.reason} | stats={result.stats}"
        )

        self._journal("live_readiness_check", {
            "ready": result.ready,
            "unlocked": self.live_unlocked,
            "reason": result.reason,
            "stats": result.stats,
            "sample_size": result.sample_size
        })

    def start(self):
        logger.info("🤖 Trading Bot Starting (Safe Mode)...")
        self.is_running = True

        broker = self.engine.broker
        if hasattr(broker, 'connect'):
            if not broker.connect():
                logger.error("❌ Failed to connect to broker. Exiting.")
                return

            start_balance = broker.get_balance()
            self.day_start_balance = start_balance
            logger.info(f"✅ Connected to broker. Start balance: ${start_balance:.2f}")
            self._journal("bot_start", {"start_balance": start_balance, "symbols": self.symbols})

        self._evaluate_live_gate()

        if self.broker_mode == "live" and not self.live_unlocked:
            logger.error("❌ LIVE mode blocked by readiness gate or allow_live_trading=false.")

        logger.info(f"📡 Scanning symbols: {self.symbols}")
        logger.info(f"⏱️ Scan interval: {self.scan_interval}s | mode={self.broker_mode}")

        while self.is_running:
            try:
                self.run_scan_cycle()
                for _ in range(self.scan_interval):
                    if not self.is_running:
                        break
                    time.sleep(1)
            except Exception as e:
                logger.error(f"⚠️ Error in bot cycle: {e}", exc_info=True)
                self._journal("bot_error", {"error": str(e)})
                time.sleep(10)

    def run_scan_cycle(self):
        logger.info(f"--- 🔄 New Scan Cycle: {datetime.now().strftime('%H:%M:%S')} ---")
        broker = self.engine.broker

        current_prices = {}
        if hasattr(broker, 'update_prices'):
            for symbol in self.symbols:
                try:
                    price = self.engine.market_data.get_current_price(symbol)
                    if price is not None and float(price) > 0:
                        current_prices[symbol] = float(price)
                        logger.info(f"💹 {symbol}: ${float(price):.2f}")
                except Exception as e:
                    logger.warning(f"Price fetch failed for {symbol}: {e}")

            if current_prices:
                broker.update_prices(current_prices)

                if hasattr(broker, 'update_trailing_stops'):
                    moved = broker.update_trailing_stops(current_prices)
                    if moved:
                        self._journal("trailing_update", {"count": len(moved), "moves": moved})

                if hasattr(broker, 'check_stop_loss_take_profit'):
                    closed = broker.check_stop_loss_take_profit(current_prices)
                    for sym, reason, pnl in closed:
                        self._journal("position_closed", {
                            "symbol": sym, "reason": reason, "pnl": float(pnl)
                        })

        current_balance = broker.get_balance()
        if hasattr(broker, 'update_balance'):
            current_balance = broker.update_balance()

        logger.info(f"💰 Balance: ${float(current_balance):.2f}")
        self._journal("balance", {"balance": float(current_balance)})

        if self.kill_switch_on_daily_loss and self._is_daily_loss_exceeded(float(current_balance)):
            self.is_running = False
            return

        open_positions = self._open_positions_count()
        logger.info(f"📌 Open positions: {open_positions}/{self.max_open_positions}")

        market_open_now = is_us_market_open(include_holidays=True)
        if self.block_orders_when_market_closed and not market_open_now:
            logger.info("🕒 US market CLOSED. New orders blocked.")

        for symbol in self.symbols:
            if not self.is_running:
                break

            try:
                signal_data = self.engine.generate_signal(symbol, force_test_mode=False)
                action = signal_data.get('action', 'hold')
                rsi = signal_data.get('rsi', 'N/A')
                logger.info(f"{symbol} signal={action} rsi={rsi}")
                self._journal("signal", {"symbol": symbol, "action": action, "rsi": rsi})
            except Exception as e:
                self._journal("signal_error", {"symbol": symbol, "error": str(e)})
                continue

            if signal_data.get('action') not in ['buy', 'sell']:
                continue

            if self.block_orders_when_market_closed and not market_open_now:
                self._journal("order_blocked", {"symbol": symbol, "reason": "market_closed"})
                continue

            open_positions = self._open_positions_count()
            if open_positions >= self.max_open_positions:
                self._journal("order_blocked", {"symbol": symbol, "reason": "max_open_positions"})
                continue

            position_size = signal_data.get('position_size', 1)
            try:
                position_size = max(1, int(float(position_size)))
            except Exception:
                position_size = 1

            # Final live safety gate
            if self.broker_mode == "live" and not self.live_unlocked:
                self._journal("order_blocked", {
                    "symbol": symbol,
                    "reason": "live_readiness_gate_locked"
                })
                logger.warning(f"🔒 Live blocked for {symbol}: readiness gate locked.")
                continue

            if hasattr(broker, 'place_order'):
                try:
                    success = broker.place_order(
                        symbol=symbol,
                        action=signal_data['action'],
                        quantity=position_size,
                        sl_price=signal_data.get('stop_loss'),
                        tp_price=signal_data.get('take_profit'),
                        entry_price=signal_data.get('entry_price'),
                        atr_value=signal_data.get('atr')
                    )

                    if success:
                        self._journal("order_executed", {
                            "symbol": symbol,
                            "action": signal_data['action'],
                            "quantity": position_size,
                            "entry_price": signal_data.get('entry_price'),
                            "stop_loss": signal_data.get('stop_loss'),
                            "take_profit": signal_data.get('take_profit'),
                            "atr": signal_data.get('atr')
                        })
                    else:
                        self._journal("order_failed", {
                            "symbol": symbol,
                            "action": signal_data['action']
                        })
                except Exception as e:
                    self._journal("order_error", {"symbol": symbol, "error": str(e)})

    def stop_bot(self, signum, frame):
        logger.info("🛑 Stopping Bot...")
        self.is_running = False
        self._journal("bot_stop", {"signal": signum})
        if hasattr(self.engine.broker, 'disconnect'):
            self.engine.broker.disconnect()
        logger.info("👋 Bot stopped gracefully.")
        sys.exit(0)


if __name__ == "__main__":
    bot = TradingBot()
    bot.start()