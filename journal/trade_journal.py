"""Trade Journal Module"""

import sqlite3
import os
from datetime import datetime
from utils.logger import setup_logger

logger = setup_logger('trade_journal')

class TradeJournal:
    def __init__(self, db_path="data/journal.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._create_table()

    def _create_table(self):
        """Create journal table if not exists"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                pair TEXT,
                action TEXT,
                entry_price REAL,
                exit_price REAL,
                profit_loss REAL,
                notes TEXT,
                emotion TEXT,
                ai_confidence REAL
            )
        ''')
        conn.commit()
        conn.close()

    def add_entry(self, pair, action, entry_price, exit_price, profit_loss, notes="", emotion="neutral", ai_confidence=0.0):
        """Add a new trade entry to the journal"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            INSERT INTO trades (date, pair, action, entry_price, exit_price, profit_loss, notes, emotion, ai_confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (datetime.now().isoformat(), pair, action, entry_price, exit_price, profit_loss, notes, emotion, ai_confidence))
        conn.commit()
        conn.close()
        logger.info(f"Journal entry added for {pair}")

    def get_entries(self, limit=20):
        """Get recent journal entries"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT * FROM trades ORDER BY date DESC LIMIT ?', (limit,))
        rows = [dict(row) for row in c.fetchall()]
        conn.close()
        return rows