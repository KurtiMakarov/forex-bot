"""Market Data Collector - Stocks only"""
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Optional
from utils.logger import setup_logger
from utils.config import Config
import yfinance as yf

logger = setup_logger('market_data')


class MarketDataCollector:
    """Collects market data from Yahoo Finance for stocks"""

    def __init__(self):
        self.config = Config()
        self.cache = {}
        self.cache_duration = 60
        logger.info("Market Data Collector initialized (Stocks only)")

    def _convert_symbol(self, symbol: str) -> str:
        """Convert symbol to Yahoo Finance format"""
        if '/' in symbol:
            return symbol.replace('/', '') + '=X'
        else:
            return symbol

    def get_historical_data(self, symbol: str, days: int = 100) -> pd.DataFrame:
        """Get historical data for a stock"""
        try:
            yahoo_symbol = self._convert_symbol(symbol)
            cache_key = f"{yahoo_symbol}_{days}"

            if cache_key in self.cache:
                cached_time, cached_data = self.cache[cache_key]
                if (datetime.now() - cached_time).seconds < self.cache_duration:
                    return cached_data

            ticker = yf.Ticker(yahoo_symbol)
            df = ticker.history(period=f"{days}d")

            if df.empty:
                logger.warning(f"No data found for {symbol}")
                return pd.DataFrame()

            df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
            df.columns = ['open', 'high', 'low', 'close', 'volume']
            df = df.reset_index()

            if 'Date' in df.columns:
                df = df.rename(columns={'Date': 'date'})
            elif 'Datetime' in df.columns:
                df = df.rename(columns={'Datetime': 'date'})

            # Drop rows with NaN values
            df = df.dropna()

            self.cache[cache_key] = (datetime.now(), df)
            logger.info(f"Successfully fetched {len(df)} real records for {symbol}")
            return df

        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {e}")
            return pd.DataFrame()

    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a stock"""
        try:
            yahoo_symbol = self._convert_symbol(symbol)
            ticker = yf.Ticker(yahoo_symbol)

            if hasattr(ticker, 'fast_info'):
                try:
                    price = ticker.fast_info.get('lastPrice', None)
                    if price is None:
                        price = ticker.fast_info.get('last_price', None)
                    if price and price > 0:
                        return float(price)
                except Exception:
                    pass

            df = ticker.history(period='1d')
            if not df.empty:
                price = df['Close'].iloc[-1]
                if pd.notna(price):
                    return float(price)

            return None

        except Exception as e:
            logger.error(f"Error fetching current price for {symbol}: {e}")
            return None

    def get_technical_indicators(self, symbol: str) -> Dict:
        """Calculate technical indicators"""
        try:
            df = self.get_historical_data(symbol, days=100)

            if df.empty or len(df) < 20:
                return {}

            close = df['close']
            high = df['high']
            low = df['low']

            # ATR
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = true_range.rolling(window=14).mean().iloc[-1]

            # RSI
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            rsi_value = rsi.iloc[-1]

            # MACD
            ema_12 = close.ewm(span=12, adjust=False).mean()
            ema_26 = close.ewm(span=26, adjust=False).mean()
            macd = ema_12 - ema_26
            signal_line = macd.ewm(span=9, adjust=False).mean()
            macd_value = macd.iloc[-1]
            signal_value = signal_line.iloc[-1]

            # Bollinger Bands
            sma_20 = close.rolling(window=20).mean()
            std_20 = close.rolling(window=20).std()
            upper_band = sma_20 + (std_20 * 2)
            lower_band = sma_20 - (std_20 * 2)

            # Moving Averages
            sma_50 = close.rolling(window=50).mean().iloc[-1] if len(close) >= 50 else None

            return {
                'atr': float(atr) if not pd.isna(atr) else None,
                'rsi': float(rsi_value) if not pd.isna(rsi_value) else None,
                'macd': float(macd_value) if not pd.isna(macd_value) else None,
                'macd_signal': float(signal_value) if not pd.isna(signal_value) else None,
                'bb_upper': float(upper_band.iloc[-1]) if not pd.isna(upper_band.iloc[-1]) else None,
                'bb_lower': float(lower_band.iloc[-1]) if not pd.isna(lower_band.iloc[-1]) else None,
                'sma_20': float(sma_20.iloc[-1]) if not pd.isna(sma_20.iloc[-1]) else None,
                'sma_50': float(sma_50) if sma_50 and not pd.isna(sma_50) else None
            }

        except Exception as e:
            logger.error(f"Error calculating indicators for {symbol}: {e}")
            return {}