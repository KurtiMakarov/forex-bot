"""Self-Learning Module - Analyzes performance and suggests improvements"""

from journal.trade_journal import TradeJournal
from statistics.performance_tracker import PerformanceTracker
from utils.logger import setup_logger
import pandas as pd
import numpy as np

logger = setup_logger('self_learner')

class SelfLearner:
    def __init__(self):
        self.journal = TradeJournal()
        self.tracker = PerformanceTracker()

    def analyze_mistakes(self, days=30):
        """Analyze recent trades to find patterns of failure"""
        entries = self.journal.get_entries(limit=100)
        if not entries:
            return {'recommendations': ['Start trading to generate data for analysis.']}

        df = pd.DataFrame(entries)

        # Filter only losing trades or negative emotions
        losing_trades = df[df['profit_loss'] < 0]
        fear_trades = df[df['emotion'].str.lower() == 'fear']

        recommendations = []

        # 1. Analysis of Losses by Pair
        if not losing_trades.empty:
            worst_pair = losing_trades['pair'].mode()[0] if not losing_trades['pair'].empty else None
            if worst_pair:
                loss_count = len(losing_trades[losing_trades['pair'] == worst_pair])
                recommendations.append(f"⚠️ Избягвай {worst_pair} - загуби в {loss_count} сделки наскоро.")

        # 2. Emotional Analysis
        if not fear_trades.empty:
            fear_loss_rate = len(fear_trades[fear_trades['profit_loss'] < 0]) / len(fear_trades)
            if fear_loss_rate > 0.6:
                recommendations.append("🧠 Търговията под влияние на 'Страх' води до загуби. Следвай плана!")

        # 3. Time-based Analysis (Simple check)
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            afternoon_losses = df[(df['date'].dt.hour >= 14) & (df['profit_loss'] < 0)]
            if len(afternoon_losses) > 3:
                recommendations.append("⏰ Следобедните сделки са рискови. Помисли за почивка след 14:00 ч.")

        if not recommendations:
            recommendations.append("✅ Системата работи стабилно. Продължавай в същия дух!")

        return {'recommendations': recommendations}

    def optimize_parameters(self, current_params):
        """Suggest parameter tweaks based on recent volatility"""
        # Placeholder for future ML integration
        return current_params