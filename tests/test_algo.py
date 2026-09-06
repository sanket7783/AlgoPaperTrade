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
        # Test XAU/USD to MCX Gold per 10g conversion
        # XAU_USD = $2500, USD_INR = 83.5, duty = 1.15
        # (2500 / 31.1034768) * 10 * 83.5 * 1.15 = ~77180.34 -> rounded to 77180.0
        mcx_price = self.mcx_engine.convert_xau_to_mcx(2500.0)
        self.assertGreater(mcx_price, 70000.0)
        self.assertLess(mcx_price, 90000.0)

    def test_paper_trade_lifecycle(self):
        initial_balance = self.mcx_engine.account_balance
        
        # Place BUY Order (1 Lot MCX GOLDM = 100g)
        order_res = self.mcx_engine.place_order(
            side="BUY",
            lots=1,
            mcx_price=77000.0,
            forex_price=2500.0,
            signal_source="TEST",
            strategy_name="TEST_STRATEGY",
            stop_loss_pct=1.0,
            take_profit_pct=2.0
        )
        self.assertEqual(order_res["status"], "OPENED")
        self.assertIsNotNone(self.mcx_engine.current_position)

        # Close position at profit (+₹500 per 10g => +₹5,000 PnL for 100g)
        close_res = self.mcx_engine.close_position(
            exit_mcx_price=77500.0,
            exit_forex_price=2515.0,
            strategy_name="TEST_STRATEGY",
            signal_source="TEST",
            reason="TAKE_PROFIT"
        )
        self.assertEqual(close_res["Trade PnL (INR)"], 5000.0)
        self.assertEqual(self.mcx_engine.account_balance, initial_balance + 5000.0)

        # Verify CSV log record created
        trades = self.logger.read_all_trades()
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0]["Instrument Name"], self.config.mcx.instrument_name)
        self.assertEqual(trades[0]["Action"], "BUY")
        self.assertEqual(float(trades[0]["Trade PnL (INR)"]), 5000.0)

    def test_strategies_generation(self):
        client = OandaClient()
        df = client.fetch_candles(granularity="M5", count=50)
        self.assertEqual(len(df), 50)

        ema_strat = EMACrossoverStrategy(self.config.strategy)
        sig1 = ema_strat.generate_signal(df, 77000.0)
        self.assertIn(sig1["signal"], ["BUY", "SELL", "NEUTRAL"])

        lead_lag_strat = LeadLagArbitrageStrategy(self.config.strategy)
        sig2 = lead_lag_strat.generate_signal(df, 77000.0)
        self.assertIn(sig2["signal"], ["BUY", "SELL", "NEUTRAL"])

        mean_rev_strat = MeanReversionStrategy(self.config.strategy)
        sig3 = mean_rev_strat.generate_signal(df, 77000.0)
        self.assertIn(sig3["signal"], ["BUY", "SELL", "NEUTRAL"])

        breakout_strat = VolatilityBreakoutStrategy(self.config.strategy)
        sig4 = breakout_strat.generate_signal(df, 77000.0)
        self.assertIn(sig4["signal"], ["BUY", "SELL", "NEUTRAL"])

    def test_algo_engine_tick(self):
        engine = AlgoTradingEngine(self.config)
        tick_data = engine.process_tick()
        self.assertIn("forex_price", tick_data)
        self.assertIn("mcx_price", tick_data)
        self.assertIn("signal", tick_data)
        self.assertIn("engine_status", tick_data)

if __name__ == "__main__":
    unittest.main()
