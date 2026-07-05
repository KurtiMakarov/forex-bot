"""Autonomous Trading Bot Runner - Stocks with Trailing Stop + RSI filter"""
import time
import sys
import os
import signal
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from signal_generator.signal_engine import SignalEngine
from utils.logger import setup_logger
from utils.config import Config

logger = setup_logger('bot_runner')


class TradingBot:
    def __init__(self):
        self.config = Config()
        self.config.set('broker.ib_client_id', 1)
        self.engine = SignalEngine()
        self.is_running = False
        self.scan_interval = 60
        self.pairs = self.config.get('data.supported_pairs', ['AAPL'])
        signal.signal(signal.SIGINT, self.stop_bot)
        signal.signal(signal.SIGTERM, self.stop_bot)

    def start(self):
        logger.info("🤖 Trading Bot Starting (Stocks Mode with Trailing Stop + RSI Filter)...")
        self.is_running = True

        broker = self.engine.broker
        if hasattr(broker, 'connect'):
            if not broker.connect():
                logger.error("❌ Failed to connect to broker. Exiting.")
                return
            logger.info(f"✅ Connected to broker. Balance: ${broker.get_balance():.2f}")

        logger.info(f"📡 Scanning stocks: {self.pairs}")
        logger.info(f"⏱️ Scan interval: {self.scan_interval} seconds")
        logger.info(f"🎯 Trailing Stop: ENABLED")
        logger.info(f"📊 RSI Filter: ENABLED (BUY blocked if RSI>70, SELL blocked if RSI<30)")

        while self.is_running:
            try:
                self.run_scan_cycle()
                for _ in range(self.scan_interval):
                    if not self.is_running:
                        break
                    time.sleep(1)
            except Exception as e:
                logger.error(f"⚠️ Error in bot cycle: {e}", exc_info=True)
                time.sleep(10)

    def run_scan_cycle(self):
        logger.info(f"--- 🔄 New Scan Cycle: {datetime.now().strftime('%H:%M:%S')} ---")

        broker = self.engine.broker

        # Update current prices
        current_prices = {}
        if hasattr(broker, 'update_prices'):
            for symbol in self.pairs:
                try:
                    price = self.engine.market_data.get_current_price(symbol)
                    if price is not None and price > 0:
                        current_prices[symbol] = price
                        logger.info(f"💹 {symbol} current price: ${price:.2f}")
                except Exception as e:
                    logger.warning(f"Could not get price for {symbol}: {e}")

            if current_prices:
                broker.update_prices(current_prices)

                # 🔥 🔥 🔥 TRAILING STOP UPDATE 🔥 🔥 🔥
                # Първо обновяваме trailing stops (преди да проверяваме SL/TP)
                if hasattr(broker, 'update_trailing_stops'):
                    moved = broker.update_trailing_stops(current_prices)
                    if moved:
                        logger.info(f"🎯 Trailing stops moved: {len(moved)} positions")

                # Check SL/TP (включително обновените trailing stops)
                if hasattr(broker, 'check_stop_loss_take_profit'):
                    closed = broker.check_stop_loss_take_profit(current_prices)
                    for sym, reason, pnl in closed:
                        logger.info(f"🔔 Position closed: {sym} ({reason}) P&L=${pnl:.2f}")

        current_balance = broker.get_balance()
        if hasattr(broker, 'update_balance'):
            current_balance = broker.update_balance()

        logger.info(f"💰 Current Balance: ${current_balance:.2f}")

        for symbol in self.pairs:
            if not self.is_running:
                break

            logger.info(f"🔍 Analyzing {symbol}...")

            try:
                signal_data = self.engine.generate_signal(symbol, force_test_mode=False)
                logger.info(f"Signal for {symbol}: {signal_data['action']} (RSI: {signal_data.get('rsi', 'N/A')})")
            except Exception as e:
                logger.error(f"Error generating signal for {symbol}: {e}")
                continue

            if signal_data['action'] in ['buy', 'sell']:
                logger.info(f"📢 SIGNAL DETECTED: {signal_data['action'].upper()} {symbol}")

                position_size = signal_data.get('position_size', 0)
                if position_size <= 0:
                    position_size = 1

                if hasattr(broker, 'place_order'):
                    try:
                        # 🔥 Подаваме ATR за trailing stop настройка
                        success = broker.place_order(
                            symbol=symbol,
                            action=signal_data['action'],
                            quantity=position_size,
                            sl_price=signal_data['stop_loss'],
                            tp_price=signal_data['take_profit'],
                            entry_price=signal_data['entry_price'],
                            atr_value=signal_data.get('atr')
                        )

                        if success:
                            logger.info(f"✅ Trade Executed for {symbol}")
                        else:
                            logger.error(f"❌ Failed to execute trade for {symbol}")
                    except Exception as e:
                        logger.error(f"Order execution error: {e}")
            else:
                logger.info(f"⏸️ {symbol}: HOLD")

    def stop_bot(self, signum, frame):
        logger.info("🛑 Stopping Bot...")
        self.is_running = False
        if hasattr(self.engine.broker, 'disconnect'):
            self.engine.broker.disconnect()
        logger.info("👋 Bot stopped gracefully.")
        sys.exit(0)


if __name__ == "__main__":
    bot = TradingBot()
    bot.start()