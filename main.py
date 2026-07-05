"""Main application entry point"""
import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

import time
from datetime import datetime
from utils.logger import setup_logger
from utils.config import Config
from signal_generator.signal_engine import SignalEngine
from backtesting.backtest_engine import BacktestEngine
from ai_ml.prediction_model import PredictionModel
from ai_ml.self_learner import SelfLearner
from statistics.performance_tracker import PerformanceTracker
from statistics.report_generator import ReportGenerator

logger = setup_logger('main', log_file='logs/trading.log')

class ForexTradingApp:
    """Main Forex Trading Application"""
    def __init__(self):
        logger.info("Initializing Forex Trading Application")
        self.config = Config()
        self.signal_engine = SignalEngine()
        self.backtest_engine = BacktestEngine()
        self.prediction_model = PredictionModel()
        self.self_learner = SelfLearner()
        self.performance_tracker = PerformanceTracker()
        self.report_generator = ReportGenerator(self.performance_tracker)
        logger.info("Application initialized successfully")

    def run_analysis(self, pair: str):
        logger.info(f"Running analysis for {pair}")
        signal = self.signal_engine.generate_signal(pair)
        ml_prediction = self.prediction_model.predict(signal.get('indicators', {}))
        adjusted_signal = self.self_learner.apply_learning(signal)
        risk_assessment = self.signal_engine.risk_calculator.assess_trade_risk(adjusted_signal, account_balance=10000)

        results = {
            'pair': pair,
            'timestamp': datetime.now().isoformat(),
            'original_signal': signal,
            'ml_prediction': ml_prediction,
            'adjusted_signal': adjusted_signal,
            'risk_assessment': risk_assessment
        }
        logger.info(f"Analysis complete for {pair}")
        return results

    def scan_market(self):
        logger.info("Scanning market")
        pairs = self.config.get('data.supported_pairs', ['EUR/USD'])
        signals = self.signal_engine.scan_market(pairs)
        logger.info(f"Market scan complete. Found {len(signals)} signals")
        return signals

    def run_backtest(self, pair: str):
        logger.info(f"Running backtest for {pair}")
        results = self.backtest_engine.run_backtest(pair)
        logger.info(f"Backtest complete for {pair}")
        return results

    def train_ml_model(self, pair: str):
        logger.info(f"Training ML model for {pair}")
        data = self.signal_engine.market_data.get_historical_data(pair, days=365)
        features = self.prediction_model.prepare_features(data)
        target = self.prediction_model.create_target(data)
        success = self.prediction_model.train(features, target)
        if success:
            logger.info("ML model trained successfully")
        else:
            logger.error("Failed to train ML model")
        return success

    def generate_report(self, report_type: str = 'daily'):
        logger.info(f"Generating {report_type} report")
        if report_type == 'daily':
            report = self.report_generator.generate_daily_report()
        elif report_type == 'weekly':
            report = self.report_generator.generate_weekly_report()
        elif report_type == 'monthly':
            report = self.report_generator.generate_monthly_report()
        else:
            report = self.report_generator.generate_daily_report()

        filename = self.report_generator.export_report(report)
        logger.info(f"Report generated: {filename}")
        return report

    def analyze_mistakes(self, days: int = 30):
        logger.info(f"Analyzing mistakes from last {days} days")
        analysis = self.self_learner.analyze_mistakes(days)
        logger.info("Mistake analysis complete")
        return analysis

    def run(self):
        logger.info("Starting Forex Trading Application")
        print("=" * 60)
        print("Forex Trading AI Application")
        print("=" * 60)

        while True:
            try:
                print("\nMenu:")
                print("1. Analyze currency pair")
                print("2. Scan market")
                print("3. Run backtest")
                print("4. Train ML model")
                print("5. Generate report")
                print("6. Analyze mistakes")
                print("7. Exit")

                choice = input("\nSelect option (1-7): ")

                if choice == '1':
                    pair = input("Enter currency pair (e.g., EUR/USD): ")
                    results = self.run_analysis(pair.upper())
                    print(f"\nAnalysis Results for {pair}:")
                    print(f"Action: {results['adjusted_signal']['action']}")
                    print(f"Confidence: {results['adjusted_signal']['confidence']:.2f}")
                    print(f"Entry Price: {results['adjusted_signal']['entry_price']}")
                    print(f"Stop Loss: {results['adjusted_signal']['stop_loss']}")
                    print(f"Take Profit: {results['adjusted_signal']['take_profit']}")

                elif choice == '2':
                    signals = self.scan_market()
                    print(f"\nMarket Scan Results:")
                    for signal in signals[:5]:
                        print(f"{signal['pair']}: {signal['action']} (confidence: {signal['confidence']:.2f})")

                elif choice == '3':
                    pair = input("Enter currency pair for backtest: ")
                    results = self.run_backtest(pair.upper())
                    print(f"\nBacktest Results:")
                    print(f"Total Return: {results['total_return']:.2f}%")
                    print(f"Total Trades: {results['total_trades']}")
                    if 'metrics' in results:
                        print(f"Sharpe Ratio: {results['metrics'].get('sharpe_ratio', 0):.2f}")
                        print(f"Max Drawdown: {results['metrics'].get('max_drawdown', 0):.2f}%")

                elif choice == '4':
                    pair = input("Enter currency pair for ML training: ")
                    success = self.train_ml_model(pair.upper())
                    print(f"ML Training: {'Success' if success else 'Failed'}")

                elif choice == '5':
                    report_type = input("Report type (daily/weekly/monthly): ")
                    report = self.generate_report(report_type)
                    print(f"\nReport Summary:")
                    print(f"Net Profit: ${report['summary']['net_profit']:.2f}")
                    print(f"Win Rate: {report['summary']['win_rate'] * 100:.1f}%")

                elif choice == '6':
                    days = int(input("Number of days to analyze (default 30): ") or 30)
                    analysis = self.analyze_mistakes(days)
                    print(f"\nMistake Analysis:")
                    print(f"Total Mistakes: {analysis.get('total_mistakes', 0)}")
                    if 'recommendations' in analysis:
                        for rec in analysis['recommendations']:
                            print(f"- {rec}")

                elif choice == '7':
                    print("Exiting application...")
                    break
                else:
                    print("Invalid option. Please try again.")

            except KeyboardInterrupt:
                print("\n\nExiting application...")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}")
                print(f"Error: {str(e)}")

if __name__ == '__main__':
    app = ForexTradingApp()
    app.run()