import sys
import time
import argparse
import uvicorn
from datetime import datetime

from config import AppConfig
from algo_engine import AlgoTradingEngine

def run_cli_mode():
    print("=" * 70)
    print("  [+] Forex Gold (OANDA XAU/USD) -> Groww MCX Gold Paper Trader (CLI)")
    print("=" * 70)
    
    config = AppConfig.load_from_file()
    engine = AlgoTradingEngine(config)

    print(f"[Config Loaded]")
    print(f" - OANDA Instrument: {config.oanda.instrument}")
    print(f" - Timeframe:        {config.oanda.timeframe}")
    print(f" - Strategy:         {config.strategy.selected_strategy}")
    print(f" - Paper Balance:    INR {config.mcx.starting_balance:,.2f}")
    print(f" - Log File:         {config.csv_file_path}")
    print("-" * 70)
    print("Press Ctrl+C to stop trading engine...\n")

    try:
        while True:
            state = engine.process_tick()
            timestamp = state['timestamp']
            forex = state['forex_price']
            mcx = state['mcx_price']
            sig = state['signal']
            status = state['engine_status']

            pos_str = "FLAT"
            if status['open_position']:
                p = status['open_position']
                pos_str = f"{p['side']} {p['lots']}L @ INR {p['entry_price']} (MTM: INR {p['unrealized_pnl']:+.2f})"

            print(f"[{timestamp}] XAU/USD: ${forex:7.2f} | MCX GOLDM: INR {mcx:8.2f} | Signal: {sig['signal']:7s} | Equity: INR {status['total_equity']:10.2f} | Pos: {pos_str}")
            
            if state.get('executed_trade_event'):
                print(f"  [TRADE EVENT] {state['executed_trade_event']}")

            time.sleep(config.update_interval_sec)
    except KeyboardInterrupt:
        print("\n[Engine Stopped] Goodbye!")

def run_ui_mode(host: str = "0.0.0.0", port: int = 8050):
    print(f"Starting Gold Algo Trading Web Dashboard at http://{host}:{port}")
    uvicorn.run("app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Forex Gold to MCX Gold Algo Trader")
    parser.add_argument("--cli", action="store_true", help="Run in headless terminal CLI mode")
    parser.add_argument("--host", default="0.0.0.0", help="Web Dashboard Host IP")
    parser.add_argument("--port", type=int, default=8000, help="Web Dashboard Port")
    args = parser.parse_args()

    if args.cli:
        run_cli_mode()
    else:
        run_ui_mode(args.host, args.port)
