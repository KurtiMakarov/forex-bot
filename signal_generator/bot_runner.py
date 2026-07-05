"""Autonomous Trading Bot Runner - Client ID 1"""
import time
import sys
import os
import signal
from datetime import datetime

# Добавяне на пътя към проекта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from signal_generator.signal_engine import SignalEngine
from utils.logger import setup_logger
from utils.config import Config

logger = setup_logger('bot_runner')


class TradingBot:
    def __init__(self):
        self.config = Config()
        # Уверяваме се, че ботът ползва ID 1
        self.config.set('broker.ib_client_id', 1)

        self.engine = SignalEngine()
        self.is_running = False
        self.scan_interval = 60

        self.pairs = self.config.get('data.supported_pairs', ['EUR/USD', 'GBP/USD'])

        # ПОПРАВКА: Премахнат е интервалът в sign al
        signal.signal(signal.SIGINT, self.stop_bot)
        signal.signal(signal.SIGTERM, self.stop_bot)

    def start(self):
        logger.info("🤖 Trading Bot Starting (Client ID 1)...")
        self.is_running = True

        broker = self.engine.broker
        if hasattr(broker, 'connect'):
            if not broker.connect():
                logger.error("❌ Failed to connect to IBKR. Exiting.")
                return
            logger.info(f"✅ Connected to IBKR. Balance: ${broker.get_balance():.2f}")

        logger.info(f"📡 Scanning pairs: {self.pairs}")
        logger.info(f"⏱️ Scan interval: {self.scan_interval} seconds")

        while self.is_running:
            try:
                self.run_scan_cycle()
                # Изчакване между сканиранията
                for _ in range(self.scan_interval):
                    if not self.is_running:
                        break
                    time.sleep(1)
            except Exception as e:
                logger.error(f"⚠️ Error in bot cycle: {e}")
                time.sleep(10)

    def run_scan_cycle(self):
        logger.info(f"--- 🔄 New Scan Cycle: {datetime.now().strftime('%H:%M:%S')} ---")

        broker = self.engine.broker
        current_balance = broker.get_balance()

        # Обновяване на баланса от IBKR
        if hasattr(broker, 'update_balance'):
            current_balance = broker.update_balance()

        logger.info(f"💰 Current Balance: ${current_balance:.2f}")

        for pair in self.pairs:
            if not self.is_running:
                break

            logger.info(f"🔍 Analyzing {pair}...")

            # Генериране на сигнал
            signal_data = self.engine.generate_signal(pair, force_test_mode=False)

            if signal_data['action'] in ['buy', 'sell']:
                logger.info(f"📢 SIGNAL DETECTED: {signal_data['action'].upper()} {pair}")
                logger.info(f"   Reason: {signal_data.get('reason', 'N/A')}")

                position_size = 0.01  # Фиксиран размер за тест

                if hasattr(broker, 'place_order'):
                    # ПОПРАВКА: take_profit вместо take _profit
                    success = broker.place_order(
                        symbol=pair.replace('/', ''),
                        action=signal_data['action'],
                        quantity=position_size,
                        sl_price=signal_data['stop_loss'],
                        tp_price=signal_data['take_profit']
                    )

                    if success:
                        logger.info(f"✅ Trade Executed for {pair}")
                        # Изпращане на уведомление
                        try:
                            self.engine.notifier.send_signal_alert(signal_data)
                        except Exception as e:
                            logger.error(f"Telegram Error: {e}")
                    else:
                        logger.error(f"❌ Failed to execute trade for {pair}")
            else:
                logger.info(f"⏸️ {pair}: HOLD")

    def stop_bot(self, signum, frame):
        logger.info("🛑 Stopping Bot...")
        self.is_running = False
        if hasattr(self.engine.broker, 'disconnect'):
            self.engine.broker.disconnect()
        logger.info("👋 Bot stopped gracefully.")
        sys.exit(0)


if __name__ == "__main__":  # ПОПРАВКА: __name__ вместо name
    bot = TradingBot()
    bot.start()