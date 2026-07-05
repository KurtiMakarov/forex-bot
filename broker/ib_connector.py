"""Interactive Brokers Connector - stocks-focused with live safety guard"""
import nest_asyncio
nest_asyncio.apply()

from ib_insync import IB, Stock, MarketOrder
from utils.logger import setup_logger
from utils.config import Config

logger = setup_logger('ib_connector')


class IBConnector:
    def __init__(self):
        self.config = Config()
        self.ib = IB()
        self.host = self.config.get('broker.ib_host', '127.0.0.1')
        self.port = int(self.config.get('broker.ib_port', 7497))
        self.client_id = int(self.config.get('broker.ib_client_id', 1))
        self.is_connected = False
        self.account_id = None
        self.last_balance = 0.0

        self.mode = self.config.get('broker.mode', 'paper')  # paper | live
        self.allow_live = bool(self.config.get('broker.allow_live_trading', False))

    def connect(self):
        if self.ib.isConnected():
            return True

        try:
            logger.info(f"Connecting to IBKR at {self.host}:{self.port} clientId={self.client_id} ...")
            self.ib.connect(self.host, self.port, clientId=self.client_id, timeout=10)

            if self.ib.isConnected():
                self.is_connected = True
                accounts = self.ib.managedAccounts()
                self.account_id = accounts[0] if accounts else "Unknown"
                logger.info(f"✅ Connected! Account: {self.account_id}")
                self._read_balance()
                return True

            return False
        except Exception as e:
            logger.error(f"❌ Connection Error: {e}")
            return False

    def _read_balance(self):
        if not self.is_connected:
            return
        try:
            values = self.ib.accountValues()
            for av in values:
                if av.tag == 'NetLiquidation' and av.account == self.account_id:
                    self.last_balance = float(av.value)
                    logger.info(f"💰 NetLiquidation: {av.value} {av.currency}")
                    return
        except Exception as e:
            logger.error(f"Balance read error: {e}")

    def update_balance(self):
        self._read_balance()
        return self.last_balance

    def get_balance(self):
        return self.last_balance

    def place_order(
        self,
        symbol: str,
        action: str,
        quantity: float,
        sl_price: float = None,
        tp_price: float = None,
        entry_price: float = None,
        atr_value: float = None
    ):
        """Place market order for STOCK symbols only."""
        if self.mode == "live" and not self.allow_live:
            logger.error("🚫 Live trading blocked by config (allow_live_trading=false).")
            return False

        if not self.is_connected:
            if not self.connect():
                return False

        try:
            symbol = symbol.upper().strip()
            qty = int(float(quantity))
            if qty <= 0:
                logger.error(f"Invalid quantity: {quantity}")
                return False

            contract = Stock(symbol, 'SMART', 'USD')
            order = MarketOrder(action.upper(), qty)

            trade = self.ib.placeOrder(contract, order)
            logger.info(f"🚀 Order placed: {action.upper()} {qty} {symbol}")

            return trade is not None
        except Exception as e:
            logger.error(f"Order Error: {e}")
            return False

    def disconnect(self):
        if self.ib.isConnected():
            self.ib.disconnect()
            self.is_connected = False
            logger.info("Disconnected from IBKR")