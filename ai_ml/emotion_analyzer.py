"""Emotion Analyzer Module"""

from journal.trade_journal import TradeJournal
from utils.logger import setup_logger

logger = setup_logger('emotion_analyzer')

class EmotionAnalyzer:
    def __init__(self):
        self.journal = TradeJournal()
        self.emotion_keywords = {
            'fear': ['strah', 'panic', 'nervous', 'fear', 'unsure'],
            'greed': ['alchnost', 'greed', 'more', 'big', 'risk'],
            'confidence': ['siguren', 'confident', 'plan', 'logic'],
            'regret': ['syzalenie', 'regret', 'missed', 'early']
        }

    def analyze_recent_emotions(self):
        """Analyze emotions from recent journal entries"""
        entries = self.journal.get_entries(limit=50)

        # Initialize counts with default values
        emotion_counts = {'fear': 0, 'greed': 0, 'confidence': 0, 'regret': 0, 'neutral': 0}

        if not entries:
            return {
                'dominant_emotion': 'neutral',
                'summary': 'No data available yet.',
                'counts': emotion_counts
            }

        for entry in entries:
            notes = str(entry.get('notes', '')).lower()
            recorded_emotion = str(entry.get('emotion', 'neutral')).lower()

            # Count recorded emotion
            if recorded_emotion in emotion_counts:
                emotion_counts[recorded_emotion] += 1

            # Keyword scanning in notes
            for emotion, keywords in self.emotion_keywords.items():
                if any(kw in notes for kw in keywords):
                    emotion_counts[emotion] += 1

        dominant = max(emotion_counts, key=emotion_counts.get)

        summary = f"Dominant emotion: {dominant.upper()}. Recent trades show a pattern of {dominant}."
        logger.info(f"Emotion Analysis: {summary}")

        # Ensure we always return 'counts'
        return {
            'dominant_emotion': dominant,
            'counts': emotion_counts,
            'summary': summary
        }