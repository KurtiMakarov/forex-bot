"""Telegram Notifier - Sends notifications for trades only"""
import requests
from utils.logger import setup_logger
from utils.config import Config

logger = setup_logger('telegram_notifier')


class TelegramNotifier:
    """Изпраща уведомления в Telegram само при отваряне/затваряне на сделки"""

    def __init__(self):
        self.config = Config()
        self.token = self.config.get('telegram.token', '')
        self.chat_id = self.config.get('telegram.chat_id', '')
        logger.info(f"Telegram Config Loaded. Token starts with: {self.token[:10]}...")

    def _send_message(self, message: str):
        """Изпраща съобщение в Telegram"""
        if not self.token or not self.chat_id or self.chat_id == 'YOUR_CHAT_ID':
            logger.debug("Telegram not configured. Skipping notification.")
            return False

        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            response = requests.post(url, data=data, timeout=5)
            if response.status_code == 200:
                logger.info("✅ Telegram message sent successfully.")
                return True
            else:
                logger.error(f"Telegram API Error: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Telegram send error: {e}")
            return False

    def send_trade_opened(self, signal: dict):
        """Изпраща уведомление при ОТВАРЯНЕ на сделка"""
        try:
            symbol = signal.get('pair', 'N/A')
            action = signal.get('action', 'N/A').upper()
            entry_price = signal.get('entry_price', 0)
            stop_loss = signal.get('stop_loss', 0)
            take_profit = signal.get('take_profit', 0)
            position_size = signal.get('position_size', 0)
            confidence = signal.get('confidence', 0)
            reason = signal.get('reason', 'N/A')

            emoji = '🟢' if action == 'BUY' else '🔴'

            message = f"""
{emoji} <b>НОВА ПОЗИЦИЯ ОТВОРЕНА</b>

📊 <b>Акция:</b> {symbol}
🎯 <b>Действие:</b> {action}
💰 <b>Размер:</b> {position_size} акции
💵 <b>Входна цена:</b> ${entry_price:.2f}
🛑 <b>Stop Loss:</b> ${stop_loss:.2f}
🎯 <b>Take Profit:</b> ${take_profit:.2f}
📈 <b>Confidence:</b> {confidence:.0%}
📝 <b>Причина:</b> {reason}
"""
            self._send_message(message)
        except Exception as e:
            logger.error(f"Error sending trade opened notification: {e}")

    def send_trade_closed(self, symbol: str, action: str, entry_price: float,
                          exit_price: float, quantity: float, pnl: float, reason: str):
        """Изпраща уведомление при ЗАТВАРЯНЕ на сделка"""
        try:
            emoji = '📈' if pnl >= 0 else '📉'
            pnl_emoji = '✅' if pnl >= 0 else '❌'

            message = f"""
{pnl_emoji} <b>ПОЗИЦИЯ ЗАТВОРЕНА</b>

📊 <b>Акция:</b> {symbol}
🎯 <b>Действие:</b> {action}
💰 <b>Размер:</b> {quantity} акции
💵 <b>Входна цена:</b> ${entry_price:.2f}
💵 <b>Изходна цена:</b> ${exit_price:.2f}
{emoji} <b>P&L:</b> ${pnl:+.2f}
📝 <b>Причина:</b> {reason}
"""
            self._send_message(message)
        except Exception as e:
            logger.error(f"Error sending trade closed notification: {e}")

    # Запазваме стария метод за съвместимост, но вече не го използваме
    def send_signal_alert(self, signal: dict):
        """Стар метод - вече не се използва"""
        pass