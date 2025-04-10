"""
Main application module for cryptocurrency trading bot.
This module coordinates all components and provides the entry point for the application.
"""

import asyncio
import json
import logging
import os
import queue
import signal
import sys
from datetime import datetime
from typing import Dict, List, Optional

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data.data_collector import DataCollector
from src.exchange.binance_exchange import BinanceExchange
from src.strategy.strategy_engine import StrategyManager
from src.execution.order_executor import OrderExecutor
from src.risk.risk_manager import RiskManager
from src.utils.monitoring import MonitoringSystem
from src.backtesting.paper_trading import PaperTradingSystem

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('crypto_trading_bot.log')
    ]
)
logger = logging.getLogger(__name__)


class TradingBot:
    """
    Main trading bot application that coordinates all components.
    """
    
    def __init__(self, config_path: str):
        """
        Initialize the trading bot.
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
        self.config = self._load_config(config_path)
        self.running = False
        self.signals_queue = queue.Queue()
        
        # Initialize components
        self._init_components()
    
    def _load_config(self, config_path: str) -> Dict:
        """
        Load configuration from file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Configuration dictionary
        """
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            logger.info(f"Loaded configuration from {config_path}")
            return config
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            # Use default configuration
            return {
                'mode': 'paper',  # 'paper' or 'live'
                'initial_capital': 10000.0,
                'exchanges': {
                    'bybit': {
                        'api_key': '',
                        'api_secret': '',
                        'trading_pairs': ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT', 'ADA/USDT', 'DOGE/USDT'],
                        'initial_balances': {'USDT': 10000.0}
                    }
                },
                'strategies': [
                    {
                        'id': 'ma_crossover_1',
                        'name': 'Moving Average Crossover',
                        'type': 'TREND_FOLLOWING',
                        'parameters': {
                            'short_window': 50,
                            'long_window': 200,
                            'volatility_scaling': True
                        },
                        'risk_parameters': {
                            'risk_per_trade': 0.02,
                            'max_position_size': 0.2
                        },
                        'target_exchanges': ['bybit'],
                        'target_pairs': ['BTC/USDT', 'ETH/USDT'],
                        'status': 'ACTIVE'
                    },
                    {
                        'id': 'arbitrage_1',
                        'name': 'Cross-Exchange Arbitrage',
                        'type': 'ARBITRAGE',
                        'parameters': {
                            'min_profit_threshold': 0.01,
                            'max_position_size': 0.2
                        },
                        'risk_parameters': {
                            'risk_per_trade': 0.01,
                            'max_position_size': 0.1
                        },
                        'target_exchanges': ['bybit'],
                        'target_pairs': ['BTC/USDT', 'ETH/USDT'],
                        'status': 'ACTIVE'
                    }
                ],
                'risk_management': {
                    'max_drawdown': 0.5,  # 50% max drawdown
                    'risk_per_trade': 0.02,  # 2% risk per trade
                    'max_exposure': 0.5,  # 50% max exposure
                    'circuit_breakers': {
                        'daily_loss_limit': 0.05,  # 5% daily loss limit
                        'weekly_loss_limit': 0.15  # 15% weekly loss limit
                    }
                },
                'monitoring': {
                    'alerts': {
                        'email': {
                            'enabled': False,
                            'smtp_server': 'smtp.gmail.com',
                            'smtp_port': 587,
                            'username': '',
                            'password': '',
                            'from_address': '',
                            'to_address': ''
                        },
                        'telegram': {
                            'enabled': False,
                            'bot_token': '',
                            'chat_id': ''
                        }
                    }
                }
            }
    
    def _init_components(self) -> None:
        """Initialize all trading bot components."""
        # Initialize exchanges
        self.exchanges = {}
        for exchange_name, exchange_config in self.config.get('exchanges', {}).items():
            self.exchanges[exchange_name] = BinanceExchange({
                **exchange_config,
                'name': exchange_name
            })
        
        # Initialize data collector
        self.data_collector = DataCollector(list(self.exchanges.values()))
        
        # Initialize risk manager
        self.risk_manager = RiskManager(self.config.get('risk_management', {}))
        
        # Initialize monitoring system
        self.monitoring_system = MonitoringSystem(
            self.config.get('monitoring', {}),
            self.risk_manager
        )
        
        # Initialize strategy manager
        self.strategy_manager = StrategyManager(self.data_collector)
        
        # Initialize order executor
        self.order_executor = OrderExecutor(self.exchanges, self.data_collector)
        
        # Initialize paper trading system if in paper mode
        if self.config.get('mode', 'paper') == 'paper':
            self.paper_trading_system = PaperTradingSystem(
                self.config,
                self.data_collector,
                self.risk_manager,
                self.monitoring_system
            )
    
    async def _load_strategies(self) -> None:
        """Load strategies from configuration."""
        for strategy_config in self.config.get('strategies', []):
            await self.strategy_manager.add_strategy(strategy_config)
            logger.info(f"Loaded strategy: {strategy_config['name']} ({strategy_config['id']})")
    
    async def _process_market_data(self) -> None:
        """Process market data through strategies."""
        # Get trading pairs from strategies
        trading_pairs = set()
        for strategy in self.strategy_manager.strategies.values():
            for pair in strategy.target_pairs:
                trading_pairs.add(pair)
        
        # Fetch data for each trading pair
        for exchange_name, exchange in self.exchanges.items():
            for pair in trading_pairs:
                if pair in exchange.exchange.trading_pairs:
                    # Fetch ticker
                    ticker = await self.data_collector.fetch_ticker(exchange_name, pair)
                    if ticker:
                        # Process through strategies
                        await self.strategy_manager.process_market_data(ticker)
    
    async def _generate_signals(self) -> None:
        """Generate trading signals from strategies."""
        signals = await self.strategy_manager.generate_signals()
        
        for signal in signals:
            self.signals_queue.put(signal)
            logger.info(f"Generated signal: {signal.direction.value} {signal.trading_pair} on {signal.exchange}")
    
    async def _execute_signals(self) -> None:
        """Execute trading signals."""
        if self.config.get('mode', 'paper') == 'paper':
            # Paper trading mode - signals are processed by paper trading system
            return
        
        # Live trading mode
        while not self.signals_queue.empty():
            signal = self.signals_queue.get_nowait()
            
            # Get current volatility
            market_data = await self.data_collector.fetch_historical_data(
                signal.exchange, signal.trading_pair, '1d', 30
            )
            
            volatility = 0.02  # Default volatility
            if market_data and len(market_data) > 1:
                # Calculate daily volatility using standard deviation of returns
                prices = [data.close_price for data in market_data]
                returns = [(prices[i] / prices[i-1]) - 1 for i in range(1, len(prices))]
                
                import statistics
                volatility = statistics.stdev(returns) if returns else 0.02
            
            # Evaluate signal against risk parameters
            is_allowed, adjusted_size, stop_loss = self.risk_manager.evaluate_signal(signal, volatility)
            
            if is_allowed:
                # Adjust signal quantity
                signal.quantity = adjusted_size
                
                # Execute signal
                order = await self.order_executor.execute_signal(signal)
                
                if order:
                    # Monitor order
                    self.monitoring_system.monitor_order(order)
                    
                    # Register position with risk manager if it's an entry
                    if signal.signal_type == "ENTRY" and order.status == "FILLED":
                        self.risk_manager.register_position(
                            position_id=f"{order.exchange}:{order.trading_pair}",
                            trading_pair=order.trading_pair,
                            size=order.filled_quantity,
                            entry_price=order.average_fill_price,
                            direction=signal.direction
                        )
    
    async def _update_positions(self) -> None:
        """Update positions with current market prices."""
        if self.config.get('mode', 'paper') == 'paper':
            # Paper trading mode - positions are updated by paper trading system
            return
        
        # Live trading mode
        positions = self.order_executor.get_positions()
        
        for position in positions:
            # Get current price
            ticker = await self.data_collector.fetch_ticker(position.exchange, position.trading_pair)
            if ticker:
                # Monitor position
                self.monitoring_system.monitor_position(position, ticker.close_price)
                
                # Update position risk
                position_id = f"{position.exchange}:{position.trading_pair}"
                current_stop = position.stop_loss_price
                
                new_stop = self.risk_manager.update_position_risk(
                    position_id, ticker.close_price, current_stop
                )
                
                if new_stop and new_stop != current_stop:
                    position.stop_loss_price = new_stop
                    logger.info(f"Updated stop-loss for {position_id}: {new_stop}")
    
    async def _update_orders(self) -> None:
        """Update order statuses."""
        if self.config.get('mode', 'paper') == 'paper':
            # Paper trading mode - orders are updated by paper trading system
            return
        
        # Live trading mode
        await self.order_executor.update_all_orders()
    
    async def _update_account_status(self) -> None:
        """Update account status."""
        if self.config.get('mode', 'paper') == 'paper':
            # Paper trading mode - account status is updated by paper trading system
            return
        
        # Live trading mode
        # Calculate total balance
        total_balance = 0.0
        
        for exchange_name, exchange in self.exchanges.items():
            balances = await exchange.fetch_balance()
            
            # Convert all balances to USD (simplified)
            for currency, amount in balances.items():
                if currency == 'USDT' or currency == 'USD':
                    total_balance += amount
                else:
                    # Get ticker for currency/USDT
                    ticker = await self.data_collector.fetch_ticker(exchange_name, f"{currency}/USDT")
                    if ticker:
                        total_balance += amount * ticker.close_price
        
        # Update risk manager and monitoring system
        self.risk_manager.update_account_status(total_balance)
        self.monitoring_system.update_balance(total_balance)
    
    async def _run_trading_cycle(self) -> None:
        """Run a complete trading cycle."""
        try:
            # Process market data
            await self._process_market_data()
            
            # Generate signals
            await self._generate_signals()
            
            # Execute signals
            await self._execute_signals()
            
            # Update positions
            await self._update_positions()
            
            # Update orders
            await self._update_orders()
            
            # Update account status
            await self._update_account_status()
            
            logger.info("Trading cycle completed")
        except Exception as e:
            logger.error(f"Error in trading cycle: {e}")
    
    async def start(self) -> None:
        """Start the trading bot."""
        if self.running:
            logger.warning("Trading bot is already running")
            return
        
        self.running = True
        logger.info("Starting trading bot")
        
        # Load strategies
        await self._load_strategies()
        
        # Start monitoring system
        monitoring_task = asyncio.create_task(
            self.monitoring_system.run_monitoring_loop()
        )
        
        # Start paper trading system if in paper mode
        if self.config.get('mode', 'paper') == 'paper':
            paper_trading_task = asyncio.create_task(
                self.paper_trading_system.run_paper_trading(self.signals_queue)
            )
        
        # Start data collection
        data_collection_task = asyncio.create_task(
            self.data_collector.start_data_collection(
                trading_pairs=[pair for exchange in self.exchanges.values() for pair in exchange.exchange.trading_pairs],
                intervals=['1m', '5m', '15m', '1h', '4h', '1d']
            )
        )
        
        # Main trading loop
        try:
            while self.running:
                await self._run_trading_cycle()
                await asyncio.sleep(60)  # Run trading cycle every minute
        except asyncio.CancelledError:
            logger.info("Trading bot stopped")
        finally:
            # Cancel all tasks
            monitoring_task.cancel()
            data_collection_task.cancel()
            
            if self.config.get('mode', 'paper') == 'paper':
                paper_trading_task.cancel()
            
            self.running = False
    
    def stop(self) -> None:
        """Stop the trading bot."""
        if not self.running:
            logger.warning("Trading bot is not running")
            return
        
        logger.info("Stopping trading bot")
        self.running = False


async def main():
    """Main entry point for the application."""
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Cryptocurrency Trading Bot')
    parser.add_argument('--config', type=str, default='config.json', help='Path to configuration file')
    args = parser.parse_args()
    
    # Create and start trading bot
    bot = TradingBot(args.config)
    
    # Handle shutdown signals
    loop = asyncio.get_event_loop()
    
    def signal_handler():
        logger.info("Shutdown signal received")
        bot.stop()
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)
    
    try:
        await bot.start()
    except Exception as e:
        logger.error(f"Error starting trading bot: {e}")
    finally:
        logger.info("Trading bot shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
