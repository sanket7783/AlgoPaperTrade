import time
from typing import Optional, Dict, Any, Tuple, List
from app_logger import log_event

try:
    from growwapi import GrowwAPI, GrowwFeed
    GROWW_SDK_AVAILABLE = True
except ImportError:
    GROWW_SDK_AVAILABLE = False

DEFAULT_MCX_GOLD_SYMBOLS = [
    {
        "symbol": "GOLDGUINEA26OCTFUT",
        "display_name": "MCX Gold Guinea (8g) - Margin ~₹6,200 [Fits ₹25k]",
        "contract_size_grams": 8.0,
        "price_unit_grams": 8.0,
        "recommended": True
    },
    {
        "symbol": "GOLDGUINEA26NOVFUT",
        "display_name": "MCX Gold Guinea Nov Fut (8g) - Margin ~₹6,200 [Fits ₹25k]",
        "contract_size_grams": 8.0,
        "price_unit_grams": 8.0,
        "recommended": False
    },
    {
        "symbol": "GOLDPETAL26OCTFUT",
        "display_name": "MCX Gold Petal (1g) - Margin ~₹800 [Fits ₹25k]",
        "contract_size_grams": 1.0,
        "price_unit_grams": 1.0,
        "recommended": False
    },
    {
        "symbol": "SILVERMIC26NOV26FUT",
        "display_name": "MCX Silver Micro (1kg) - Margin ~₹8,500 [Fits ₹25k]",
        "contract_size_grams": 1000.0,
        "price_unit_grams": 1000.0,
        "recommended": False
    },
    {
        "symbol": "GOLDM26OCTFUT",
        "display_name": "MCX Gold Mini (100g) - Margin ~₹78,000 [Needs >₹80k]",
        "contract_size_grams": 100.0,
        "price_unit_grams": 10.0,
        "recommended": False
    },
    {
        "symbol": "GOLD26OCTFUT",
        "display_name": "MCX Gold Mega (1kg) - Margin ~₹7,80,000",
        "contract_size_grams": 1000.0,
        "price_unit_grams": 10.0,
        "recommended": False
    }
]

class GrowwMCXClient:
    """
    Client for fetching live MCX Gold Mini/Guinea quotes and discovering symbols from Groww API.
    """
    def __init__(self, api_key: str = "", api_secret: str = "", access_token: str = ""):
        self.api_key = api_key.strip() if api_key else ""
        self.api_secret = api_secret.strip() if api_secret else ""
        self.access_token = access_token.strip() if access_token else ""
        self.groww_api: Optional[Any] = None
        self.is_authenticated = False
        
        self.init_groww_sdk()

    def init_groww_sdk(self):
        self.access_token = self.access_token.strip() if self.access_token else ""
        
        if not GROWW_SDK_AVAILABLE:
            log_event("WARNING", "SYSTEM", "growwapi package not available in environment.")
            self.is_authenticated = False
            return

        if self.access_token:
            try:
                self.groww_api = GrowwAPI(token=self.access_token)
                self.is_authenticated = True
                log_event("INFO", "SYSTEM", f"Groww MCX SDK initialized with Access Token ({self.access_token[:6]}...{self.access_token[-4:]})")
            except Exception as e:
                log_event("WARNING", "SYSTEM", f"Could not authenticate Groww SDK with token: {e}")
                self.is_authenticated = False
        elif self.api_key and self.api_secret:
            try:
                token_resp = GrowwAPI.get_access_token(api_key=self.api_key, secret=self.api_secret)
                if isinstance(token_resp, dict) and "access_token" in token_resp:
                    self.access_token = token_resp["access_token"]
                    self.groww_api = GrowwAPI(token=self.access_token)
                    self.is_authenticated = True
                    log_event("INFO", "SYSTEM", "Groww MCX SDK authenticated via API Key & Secret.")
            except Exception as e:
                log_event("WARNING", "SYSTEM", f"Groww get_access_token failed: {e}")
                self.is_authenticated = False
        else:
            self.is_authenticated = False
            self.groww_api = None

    def validate_token(self, token: Optional[str] = None) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Actively checks if the provided Groww access token is valid by querying the Groww user profile.
        """
        target_token = (token or self.access_token).strip() if (token or self.access_token) else ""
        if not GROWW_SDK_AVAILABLE:
            return False, "growwapi library is not installed in the environment", {}
        if not target_token:
            return False, "Groww access token is missing or empty", {}

        try:
            temp_api = GrowwAPI(token=target_token)
            profile = temp_api.get_user_profile()
            name = ""
            if isinstance(profile, dict):
                name = profile.get("name") or profile.get("userName") or profile.get("email") or ""
            msg = f"Groww Token is VALID (User: {name})" if name else "Groww Token is VALID (Authenticated)"
            return True, msg, profile if isinstance(profile, dict) else {}
        except Exception as e:
            err_str = str(e)
            if "expired" in err_str.lower() or "invalid" in err_str.lower() or "authentication" in err_str.lower():
                return False, "Groww Authentication Failed: Token has expired or is invalid.", {}
            return False, f"Groww Verification Error: {err_str}", {}

    def get_available_symbols(self) -> List[Dict[str, Any]]:
        """
        Returns selectable MCX Gold commodity contracts.
        Queries live Groww expiries if authenticated.
        """
        symbols = list(DEFAULT_MCX_GOLD_SYMBOLS)
        if self.is_authenticated and self.groww_api:
            try:
                # Try fetching live active expiries from Groww
                expiries_resp = self.groww_api.get_expiries(exchange=GrowwAPI.EXCHANGE_MCX, underlying_symbol="GOLDGUINEA")
                if isinstance(expiries_resp, dict) and "expiries" in expiries_resp:
                    log_event("INFO", "POLLING", f"Discovered live Groww expiries for GOLDGUINEA: {expiries_resp['expiries'][:3]}")
            except Exception as e:
                # Non-critical discovery error; defaults remain active
                pass
        return symbols

    def fetch_live_mcx_ltp(self, trading_symbol: str = "GOLDGUINEA26OCTFUT") -> Optional[float]:
        """
        Fetches live Last Traded Price (LTP) for MCX Gold Mini/Guinea from Groww API.
        """
        if self.is_authenticated and self.groww_api:
            try:
                sym = trading_symbol.strip()
                if not sym.startswith("MCX_"):
                    sym = f"MCX_{sym}"
                
                ltp_data = self.groww_api.get_ltp(
                    exchange_trading_symbols=(sym,),
                    segment=GrowwAPI.SEGMENT_COMMODITY
                )
                if isinstance(ltp_data, dict):
                    price = ltp_data.get(sym) or ltp_data.get("ltp") or ltp_data.get("last_price")
                    if price:
                        price_flt = float(price)
                        log_event("INFO", "POLLING", f"Groww MCX API Poll: Symbol {sym} LTP = ₹{price_flt:,.2f}")
                        return price_flt
            except Exception as e:
                log_event("ERROR", "POLLING", f"Failed to poll Groww MCX LTP for {trading_symbol}: {e}")
        return None

    def fetch_quote(self, trading_symbol: str = "GOLDGUINEA26OCTFUT") -> Optional[Dict[str, Any]]:
        if self.is_authenticated and self.groww_api:
            try:
                sym = trading_symbol.strip()
                if not sym.startswith("MCX_"):
                    sym = f"MCX_{sym}"
                quote = self.groww_api.get_quote(
                    exchange_trading_symbols=(sym,),
                    segment=GrowwAPI.SEGMENT_COMMODITY
                )
                log_event("INFO", "POLLING", f"Groww MCX Quote Poll: Symbol {sym} fetched.")
                return quote
            except Exception as e:
                log_event("ERROR", "POLLING", f"Groww MCX Quote error for {trading_symbol}: {e}")
        return None
