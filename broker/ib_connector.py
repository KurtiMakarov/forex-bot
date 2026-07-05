"""Interactive Brokers Connector"""
import nest_asyncio
nest_asyncio.apply()

from ib_insync import IB, Forex, MarketOrder
from utils.logger import setup_logger
from utils.config import Config
import time

logger = setup_logger('ib_connector')

class IBConnector:
    def __init__(self):
        self.config = Config()
        self.ib = IB()
        self.host = self.config.get('broker.ib_host', '127.0.0.1')
        self.port = self.config.get('broker.ib_port', 4001)
        self.client_id = self.config.get('broker.ib_client_id', 1)
        self.is_connected = False
        self.account_id = None
        self.last_balance = 0.0

    def connect(self):
        if self.ib.isConnected():
            return True
        try:
            logger.info(f"Connecting to IBKR at {self.host}:{self.port}...")
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
                    logger.info(f"💰 Balance Found: {av.value} {av.currency}")
                    return
        except Exception as e:
            logger.error(f"Balance read error: {e}")

    def update_balance(self):
        self._read_balance()
        return self.last_balance

    def get_balance(self):
        return self.last_balance

    def place_order(self, symbol: str, action: str, quantity: float, 
                    sl_price: float = None, tp_price: float = None):
        if not self.is_connected:
            if not self.connect():
                return False
        try:
            if len(symbol) != 6 or not symbol.isalpha():
                logger.error(f"Invalid symbol: {symbol}")
                return False
            contract = Forex(symbol[:3], symbol[3:])
            order = MarketOrder(action.upper(), quantity)
            self.ib.placeOrder(contract, order)
            logger.info(f"🚀 Order placed: {action} {quantity} {symbol}")
            return True
        except Exception as e:
            logger.error(f"Order Error: {e}")
            return False

    def disconnect(self):
        if self.ib.isConnected():
            self.ib.disconnect()
            self.is_connected = False