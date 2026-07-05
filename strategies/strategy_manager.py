"""Strategy Manager - Combined EMA + RSI Strategy"""
import pandas as pd
import numpy as np
from typing import Dict
from utils.logger import setup_logger

logger = setup_logger('strategy_manager')


class StrategyManager:
    """Combined EMA Crossover + RSI Strategy"""

    def __init__(self):
        self.strategies = {
            'ema_crossover': 0.5,
            'rsi_reversal': 0.5
        }
        logger.info(f"Initialized COMBINED Strategy: EMA + RSI")

    def get_combined_signal(self, historical_data: pd.DataFrame, current_price: float) -> Dict:
        """
        Combined strategy:
        - BUY if EMA9 > EMA21 OR RSI < 30
        - SELL if EMA9 < EMA21 OR RSI > 70
        - HOLD otherwise
        """
        try:
            if historical_data.empty or len(historical_data) < 30:
                return {'action': 'hold', 'confidence': 0, 'reason': 'Not enough data'}

            close = historical_data['close']

            # ===== EMA 9 и EMA 21 =====
            ema_9 = close.ewm(span=9, adjust=False).mean()
            ema_21 = close.ewm(span=21, adjust=False).mean()

            ema_9_current = ema_9.iloc[-1]
            ema_21_current = ema_21.iloc[-1]
            ema_9_prev = ema_9.iloc[-2]
            ema_21_prev = ema_21.iloc[-2]

            # ===== RSI =====
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            rsi_value = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50

            # ===== MACD (за потвърждение) =====
            ema_12 = close.ewm(span=12, adjust=False).mean()
            ema_26 = close.ewm(span=26, adjust=False).mean()
            macd_line = ema_12 - ema_26
            signal_line = macd_line.ewm(span=9, adjust=False).mean()
            macd_value = macd_line.iloc[-1]
            signal_value = signal_line.iloc[-1]

            # ===== СИГНАЛИ =====

            # 🔥 EMA Crossover сигнали
            ema_buy = (ema_9_prev <= ema_21_prev) and (ema_9_current > ema_21_current)
            ema_sell = (ema_9_prev >= ema_21_prev) and (ema_9_current < ema_21_current)

            # 🔥 EMA Trend (ако няма crossover)
            ema_trend_buy = ema_9_current > ema_21_current
            ema_trend_sell = ema_9_current < ema_21_current

            # 🔥 RSI сигнали (свръхкупени/свърхпродадени)
            rsi_oversold = rsi_value < 30  # Време за BUY
            rsi_overbought = rsi_value > 70  # Време за SELL

            # ===== КОМБИНИРАНА ЛОГИКА =====

            # 🔥 СИЛНИ сигнали (EMA crossover + RSI потвърждение)
            if ema_buy and rsi_value < 65:
                action = 'buy'
                confidence = 0.90
                reason = f"EMA BUY crossover + RSI: {rsi_value:.0f}"
                logger.info(f"🟢 STRONG BUY: EMA crossover confirmed by RSI")

            elif ema_sell and rsi_value > 35:
                action = 'sell'
                confidence = 0.90
                reason = f"EMA SELL crossover + RSI: {rsi_value:.0f}"
                logger.info(f"🔴 STRONG SELL: EMA crossover confirmed by RSI")

            # 🔥 RSI reversal сигнали (когато EMA няма crossover)
            elif rsi_oversold:
                action = 'buy'
                confidence = 0.75
                reason = f"RSI oversold ({rsi_value:.0f} < 30) - reversal expected"
                logger.info(f"🟢 RSI BUY: Oversold condition detected")

            elif rsi_overbought:
                action = 'sell'
                confidence = 0.75
                reason = f"RSI overbought ({rsi_value:.0f} > 70) - reversal expected"
                logger.info(f"🔴 RSI SELL: Overbought condition detected")

            # 🔥 EMA trend сигнали (ако няма crossover и RSI е неутрален)
            elif ema_trend_buy and macd_value > signal_value:
                action = 'buy'
                confidence = 0.65
                reason = f"EMA trend up + MACD bullish | RSI: {rsi_value:.0f}"
                logger.info(f"🟢 TREND BUY: EMA9 > EMA21 + MACD confirmed")

            elif ema_trend_sell and macd_value < signal_value:
                action = 'sell'
                confidence = 0.65
                reason = f"EMA trend down + MACD bearish | RSI: {rsi_value:.0f}"
                logger.info(f"🔴 TREND SELL: EMA9 < EMA21 + MACD confirmed")

            # 🔥 HOLD (няма ясен сигнал)
            else:
                action = 'hold'
                confidence = 0.30
                reason = f"No clear signal | EMA9: {ema_9_current:.2f} | EMA21: {ema_21_current:.2f} | RSI: {rsi_value:.0f}"

            logger.info(f"📊 Strategy: {action.upper()} | EMA9: {ema_9_current:.2f} | EMA21: {ema_21_current:.2f} | RSI: {rsi_value:.0f} | MACD: {'↑' if macd_value > signal_value else '↓'}")

            return {
                'action': action,
                'confidence': confidence,
                'reason': reason,
                'ema_9': ema_9_current,
                'ema_21': ema_21_current,
                'rsi': rsi_value,
                'macd': macd_value,
                'macd_signal': signal_value
            }

        except Exception as e:
            logger.error(f"Strategy error: {e}")
            return {'action': 'hold', 'confidence': 0, 'reason': f'Error: {str(e)}'}