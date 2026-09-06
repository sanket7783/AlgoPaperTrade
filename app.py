import os
import json
import asyncio
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

from config import AppConfig
from algo_engine import AlgoTradingEngine
from app_logger import get_recent_logs, log_event

app = FastAPI(title="Forex Gold to MCX Gold Algo Paper Trader", version="1.0.0")

# Load configuration and initialize algo engine
config = AppConfig.load_from_file()
algo_engine = AlgoTradingEngine(config)

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()

# Background tick loop task
async def background_tick_loop():
    log_event("INFO", "SYSTEM", "Background polling & trading loop started.")
    while True:
        try:
            tick_data = algo_engine.process_tick()
            tick_data["recent_logs"] = get_recent_logs(20)
            await manager.broadcast(tick_data)
        except Exception as e:
            log_event("ERROR", "SYSTEM", f"Tick processing error: {e}")
        await asyncio.sleep(algo_engine.config.update_interval_sec)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(background_tick_loop())

# REST API Endpoints
@app.get("/api/status")
def get_status():
    tick_data = algo_engine.process_tick()
    return {
        "config": algo_engine.config,
        "state": tick_data,
        "trade_history": algo_engine.mcx_engine.trade_history,
        "recent_logs": get_recent_logs(50)
    }

@app.get("/api/logs")
def get_logs(limit: int = 50):
    return {"logs": get_recent_logs(limit)}

class ConfigUpdateModel(BaseModel):
    oanda_api_token: str
    oanda_account_id: str
    oanda_environment: str
    groww_access_token: Optional[str] = ""
    groww_trading_symbol: Optional[str] = "GOLDM26OCTFUT"
    timeframe: str
    selected_strategy: str
    starting_balance: float
    stop_loss_pct: float
    take_profit_pct: float
    fast_ema: int = 9
    slow_ema: int = 21

@app.post("/api/config")
def update_config(cfg: ConfigUpdateModel):
    current = algo_engine.config
    current.oanda.api_token = cfg.oanda_api_token
    current.oanda.account_id = cfg.oanda_account_id
    current.oanda.environment = cfg.oanda_environment
    current.oanda.timeframe = cfg.timeframe
    
    if cfg.groww_access_token is not None:
        current.mcx.groww_access_token = cfg.groww_access_token
    if cfg.groww_trading_symbol:
        current.mcx.groww_trading_symbol = cfg.groww_trading_symbol

    current.strategy.selected_strategy = cfg.selected_strategy
    current.strategy.stop_loss_pct = cfg.stop_loss_pct
    current.strategy.take_profit_pct = cfg.take_profit_pct
    current.strategy.fast_ema = cfg.fast_ema
    current.strategy.slow_ema = cfg.slow_ema
    
    if cfg.starting_balance != current.mcx.starting_balance:
        current.mcx.starting_balance = cfg.starting_balance
        algo_engine.mcx_engine.account_balance = cfg.starting_balance

    algo_engine.update_config(current)
    current.save_to_file()
    log_event("INFO", "SYSTEM", f"Configuration & API tokens updated from UI. Strategy: {cfg.selected_strategy}, Timeframe: {cfg.timeframe}")
    return {"status": "SUCCESS", "config": current}

class ManualTradeModel(BaseModel):
    action: str
    lots: int = 1

@app.post("/api/trade/manual")
def manual_trade(trade: ManualTradeModel):
    action = trade.action.upper()
    mcx_price = algo_engine.latest_mcx_price
    forex_price = algo_engine.latest_forex_price
    tf = algo_engine.config.oanda.timeframe

    log_event("INFO", "ORDER", f"Manual trade button triggered from Web UI: {action} ({trade.lots} Lot)")

    if action in ["BUY", "SELL"]:
        res = algo_engine.mcx_engine.place_order(
            side=action,
            lots=trade.lots,
            mcx_price=mcx_price,
            forex_price=forex_price,
            signal_source=f"MANUAL_TRIGGER_{tf}",
            strategy_name=algo_engine.current_strategy.name,
            stop_loss_pct=algo_engine.config.strategy.stop_loss_pct,
            take_profit_pct=algo_engine.config.strategy.take_profit_pct
        )
        return res
    elif action == "SQUARE_OFF":
        res = algo_engine.mcx_engine.close_position(
            exit_mcx_price=mcx_price,
            exit_forex_price=forex_price,
            strategy_name=algo_engine.current_strategy.name,
            signal_source=f"MANUAL_SQUARE_OFF_{tf}",
            reason="MANUAL_SQUARE_OFF"
        )
        return {"status": "CLOSED", "trade": res}
    else:
        raise HTTPException(status_code=400, detail="Invalid action")

class SimulateSignalModel(BaseModel):
    signal: str

@app.post("/api/trade/simulate_signal")
def simulate_signal(data: SimulateSignalModel):
    sig = data.signal.upper()
    if sig not in ["BUY", "SELL"]:
        raise HTTPException(status_code=400, detail="Invalid signal")

    mcx_price = algo_engine.latest_mcx_price
    forex_price = algo_engine.latest_forex_price
    tf = algo_engine.config.oanda.timeframe

    log_event("INFO", "SIGNAL", f"Simulated Auto Signal Triggered from UI: {sig}")

    res = algo_engine.mcx_engine.place_order(
        side=sig,
        lots=algo_engine.config.strategy.max_lots_per_trade,
        mcx_price=mcx_price,
        forex_price=forex_price,
        signal_source=f"AUTO_SIGNAL_{sig}_{tf}",
        strategy_name=algo_engine.current_strategy.name,
        stop_loss_pct=algo_engine.config.strategy.stop_loss_pct,
        take_profit_pct=algo_engine.config.strategy.take_profit_pct
    )
    return res

@app.post("/api/autotrade/toggle")
def toggle_autotrade():
    algo_engine.auto_trade_enabled = not algo_engine.auto_trade_enabled
    state = "ENABLED" if algo_engine.auto_trade_enabled else "DISABLED"
    log_event("INFO", "SYSTEM", f"Auto Trading state toggled from UI: {state}")
    return {"auto_trade_enabled": algo_engine.auto_trade_enabled}

@app.get("/api/trades/csv")
def download_csv():
    csv_path = algo_engine.config.csv_file_path
    if not os.path.exists(csv_path):
        algo_engine.csv_logger._ensure_header()
    log_event("INFO", "SYSTEM", f"CSV Report downloaded by user: {csv_path}")
    return FileResponse(
        path=csv_path,
        filename="mcx_gold_trades_pnl.csv",
        media_type="text/csv"
    )

static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)

@app.get("/")
def read_root():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h2>Dashboard HTML loading...</h2>")

app.mount("/static", StaticFiles(directory=static_dir), name="static")
