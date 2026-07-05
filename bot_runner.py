"""Autonomous Trading Bot Runner - Stocks with safety guardrails + journaling"""
import time
import sys
import os
import signal
import json
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

        self.broker_mode = self.config.get('broker.mode', 'paper')
        self.allow_live = self.config.get('broker.allow_live_trading', False)

        self.max_daily_loss = float(self.config.get('trading.max_daily_loss', 0.02))
        self.kill_switch_on_daily_loss = bool(self.config.get('trading.kill_switch_on_daily_loss', True))

        self.day_start_balance = None
        self.journal_path = "journal/trades.jsonl"
        os.makedirs("journal", exist_ok=True)

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
