import time
from typing import Optional, Dict, Any
from app_logger import log_event

try:
    from growwapi import GrowwAPI, GrowwFeed
    GROWW_SDK_AVAILABLE = True
except ImportError:
    GROWW_SDK_AVAILABLE = False

class GrowwMCXClient:
    """
    Client for fetching live MCX Gold Mini quotes and placing order requests via Groww API.
    Fallback to calculated Forex-derived MCX price when Groww API key is not provided.
    """
    def __init__(self, api_key: str = "", api_secret: str = "", access_token: str = ""):
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = access_token
        self.groww_api: Optional[Any] = None
        self.is_authenticated = False
        
        self.init_groww_sdk()

    def init_groww_sdk(self):
        if GROWW_SDK_AVAILABLE and self.access_token:
            try:
                self.groww_api = GrowwAPI(token=self.access_token)
                self.is_authenticated = True
                log_event("INFO", "SYSTEM", "Groww MCX API SDK authenticated successfully.")
            except Exception as e:
                log_event("WARNING", "SYSTEM", f"Could not authenticate Groww SDK: {e}")
                self.is_authenticated = False
        else:
            self.is_authenticated = False

    def fetch_live_mcx_ltp(self, trading_symbol: str = "GOLDM26OCTFUT") -> Optional[float]:
        """
        Fetches live Last Traded Price (LTP) for MCX Gold Mini from Groww API.
        """
        if self.is_authenticated and self.groww_api:
            try:
                ltp_data = self.groww_api.get_ltp(exchange=GrowwAPI.EXCHANGE_MCX, trading_symbol=trading_symbol)
                if isinstance(ltp_data, dict):
                    price = ltp_data.get("ltp") or ltp_data.get("last_price")
                    if price:
                        price_flt = float(price)
                        log_event("INFO", "POLLING", f"Groww MCX API Poll: Symbol {trading_symbol} LTP = ₹{price_flt:,.2f}")
                        return price_flt
            except Exception as e:
                log_event("ERROR", "POLLING", f"Failed to poll Groww MCX LTP for {trading_symbol}: {e}")
        return None

    def fetch_quote(self, trading_symbol: str = "GOLDM26OCTFUT") -> Optional[Dict[str, Any]]:
        if self.is_authenticated and self.groww_api:
            try:
                quote = self.groww_api.get_quote(exchange=GrowwAPI.EXCHANGE_MCX, trading_symbol=trading_symbol)
                log_event("INFO", "POLLING", f"Groww MCX Quote Poll: Symbol {trading_symbol} fetched.")
                return quote
            except Exception as e:
                log_event("ERROR", "POLLING", f"Groww MCX Quote error for {trading_symbol}: {e}")
        return None
