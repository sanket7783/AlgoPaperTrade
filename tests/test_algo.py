import unittest
import os
import pandas as pd
from datetime import datetime

from config import AppConfig
from oanda_client import OandaClient
from csv_logger import CSVTradeLogger
from mcx_engine import MCXPaperTradingEngine
from algo_engine import AlgoTradingEngine
from strategies import EMACrossoverStrategy, LeadLagArbitrageStrategy, MeanReversionStrategy, VolatilityBreakoutStrategy

class TestAlgoPaperTrader(unittest.TestCase):
    def setUp(self):
        self.test_csv = "test_trades.csv"
        if os.path.exists(self.test_csv):
            os.remove(self.test_csv)
            
        self.config = AppConfig()
        self.config.csv_file_path = self.test_csv
        self.logger = CSVTradeLogger(filepath=self.test_csv)
        self.mcx_engine = MCXPaperTradingEngine(config=self.config.mcx, csv_logger=self.logger)

    def tearDown(self):
        if os.path.exists(self.test_csv):
            os.remove(self.test_csv)

    def test_price_conversion(self):
        # Test XAU/USD to MCX Gold Guinea (8g) conversion
        # XAU_USD = $2500, USD_INR = 83.5, duty = 1.15
        # (2500 / 31.1034768) * 8 * 83.5 * 1.15 = ~61744.27 -> rounded to 61744.0
        mcx_price = self.mcx_engine.convert_xau_to_mcx(2500.0)
        self.assertGreater(mcx_price, 50000.0)
        self.assertLess(mcx_price, 75000.0)

    def test_paper_trade_lifecycle_both_sides(self):
        initial_balance = self.mcx_engine.account_balance
        
        # 1. Place BUY Order (1 Lot MCX Gold Guinea = 8g)
        order_res = self.mcx_engine.place_order(
            side="BUY",
            lots=1,
            mcx_price=61700.0,
            forex_price=2500.0,
            signal_source="TEST",
            strategy_name="TEST_STRATEGY",
            stop_loss_pct=1.0,
            take_profit_pct=2.0
        )
        self.assertEqual(order_res["status"], "OPENED")
        self.assertIsNotNone(self.mcx_engine.current_position)

        # 2. Close position at profit (+₹500 per guinea => +₹500 PnL for 8g)
        close_res = self.mcx_engine.close_position(
            exit_mcx_price=62200.0,
            exit_forex_price=2520.0,
            strategy_name="TEST_STRATEGY",
            signal_source="TEST",
            reason="TAKE_PROFIT"
        )
        self.assertEqual(close_res["Trade PnL (INR)"], 500.0)
        self.assertEqual(self.mcx_engine.account_balance, initial_balance + 500.0)

        # 3. Verify that BOTH BUY (ENTRY) and SELL (EXIT) trades are printed/logged
        trades = self.logger.read_all_trades()
        self.assertEqual(len(trades), 2)
        self.assertEqual(trades[0]["Action"], "BUY (ENTRY)")
        self.assertEqual(trades[0]["Status"], "OPENED")
        self.assertEqual(trades[1]["Action"], "SELL (EXIT)")
        self.assertEqual(trades[1]["Status"], "TAKE_PROFIT")
        self.assertEqual(float(trades[1]["Trade PnL (INR)"]), 500.0)

    def test_strategies_generation(self):
        client = OandaClient()
        df = client.fetch_candles(granularity="M5", count=50, live_only=False)
        self.assertEqual(len(df), 50)

        ema_strat = EMACrossoverStrategy(self.config.strategy)
        sig1 = ema_strat.generate_signal(df, 61700.0)
        self.assertIn(sig1["signal"], ["BUY", "SELL", "NEUTRAL"])

        lead_lag_strat = LeadLagArbitrageStrategy(self.config.strategy)
        sig2 = lead_lag_strat.generate_signal(df, 61700.0)
        self.assertIn(sig2["signal"], ["BUY", "SELL", "NEUTRAL"])

        mean_rev_strat = MeanReversionStrategy(self.config.strategy)
        sig3 = mean_rev_strat.generate_signal(df, 61700.0)
        self.assertIn(sig3["signal"], ["BUY", "SELL", "NEUTRAL"])

        breakout_strat = VolatilityBreakoutStrategy(self.config.strategy)
        sig4 = breakout_strat.generate_signal(df, 61700.0)
        self.assertIn(sig4["signal"], ["BUY", "SELL", "NEUTRAL"])

    def test_algo_engine_tick(self):
        engine = AlgoTradingEngine(self.config)
        tick_data = engine.process_tick()
        self.assertIn("forex_price", tick_data)
        self.assertIn("mcx_price", tick_data)
        self.assertIn("signal", tick_data)
        self.assertIn("engine_status", tick_data)

    def test_token_validation(self):
        oanda_client = OandaClient(api_token="DEMO_TOKEN_PLACEHOLDER")
        o_valid, o_msg, _ = oanda_client.validate_token()
        self.assertFalse(o_valid)
        self.assertIn("placeholder", o_msg.lower())

        from groww_mcx_client import GrowwMCXClient
        groww_client = GrowwMCXClient(access_token="")
        g_valid, g_msg, _ = groww_client.validate_token()
        self.assertFalse(g_valid)
        self.assertIn("missing", g_msg.lower())

    def test_live_only_blocks_synthetic_trades(self):
        self.config.live_market_only = True
        engine = AlgoTradingEngine(self.config)
        tick = engine.process_tick()
        self.assertEqual(tick["signal"]["signal"], "NEUTRAL")
        self.assertIn("Live Market Only", tick["signal"]["reason"])
        self.assertIsNone(tick["executed_trade_event"])

if __name__ == "__main__":
    unittest.main()
