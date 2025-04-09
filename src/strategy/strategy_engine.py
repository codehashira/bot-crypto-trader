"""
Strategy engine module for cryptocurrency trading bot.
This module implements the strategy framework for generating trading signals.
"""

import abc
import logging
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union

from ..models.base_models import (
    MarketData, Order, OrderSide, OrderType, Position, PositionSide, Signal, SignalType, Strategy, StrategyType, Trade
)
from ..data.data_collector import DataCollector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StrategyBase(abc.ABC):
    """Abstract base class for trading strategies."""
    
    def __init__(self, strategy_config: Strategy, data_collector: DataCollector):
        """
        Initialize the strategy.
        
        Args:
            strategy_config: Strategy configuration
            data_collector: Data collector instance
        """
        self.config = strategy_config
        self.data_collector = data_collector
        self.id = strategy_config.id
        self.name = strategy_config.name
        self.type = strategy_config.type
        self.parameters = strategy_config.parameters
        self.risk_parameters = strategy_config.risk_parameters
        self.target_exchanges = strategy_config.target_exchanges
        self.target_pairs = strategy_config.target_pairs
        self.status = strategy_config.status
        
        # Internal state
        self.positions = {}  # Dict to track current positions
        self.orders = {}     # Dict to track open orders
        self.signals = []    # List of generated signals
        
    @abc.abstractmethod
    async def process_market_data(self, market_data: MarketData) -> None:
        """
        Process new market data and update internal state.
        
        Args:
            market_data: New market data
        """
        pass
    
    @abc.abstractmethod
    async def generate_signals(self) -> List[Signal]:
        """
        Generate trading signals based on current market conditions.
        
        Returns:
            List of Signal objects
        """
        pass
    
    async def on_order_update(self, order: Order) -> None:
        """
        Handle order status updates.
        
        Args:
            order: Updated order
        """
        # Update internal order tracking
        self.orders[order.id] = order
        
        # If order is filled, update position
        if order.status == OrderStatus.FILLED:
            await self._update_position(order)
    
    async def on_trade(self, trade: Trade) -> None:
        """
        Handle completed trades.
        
        Args:
            trade: Completed trade
        """
        # Update internal trade tracking
        logger.info(f"Trade completed: {trade.id} for {trade.trading_pair} on {trade.exchange}")
    
    async def _update_position(self, order: Order) -> None:
        """
        Update position based on filled order.
        
        Args:
            order: Filled order
        """
        position_key = f"{order.exchange}:{order.trading_pair}"
        
        # Determine position side
        side = PositionSide.LONG if order.side == OrderSide.BUY else PositionSide.SHORT
        
        # If position exists, update it
        if position_key in self.positions:
            position = self.positions[position_key]
            
            # If same side, increase position
            if position.side == side:
                # Calculate new average entry price
                total_value = (position.entry_price * position.quantity) + (order.average_fill_price * order.filled_quantity)
                total_quantity = position.quantity + order.filled_quantity
                new_entry_price = total_value / total_quantity if total_quantity > 0 else 0
                
                # Update position
                position.entry_price = new_entry_price
                position.quantity += order.filled_quantity
                position.last_update_time = datetime.now()
            else:
                # Opposite side, reduce position
                if order.filled_quantity >= position.quantity:
                    # Position closed
                    realized_pnl = self._calculate_pnl(position, order)
                    logger.info(f"Position closed: {position_key} with PnL: {realized_pnl}")
                    del self.positions[position_key]
                else:
                    # Position reduced
                    realized_pnl = self._calculate_pnl(position, order)
                    position.quantity -= order.filled_quantity
                    position.realized_pnl += realized_pnl
                    position.last_update_time = datetime.now()
                    logger.info(f"Position reduced: {position_key} to {position.quantity} with PnL: {realized_pnl}")
        else:
            # New position
            if order.side == OrderSide.BUY:
                # Long position
                position = Position(
                    exchange=order.exchange,
                    trading_pair=order.trading_pair,
                    side=PositionSide.LONG,
                    entry_price=order.average_fill_price,
                    quantity=order.filled_quantity,
                    strategy_id=self.id
                )
                self.positions[position_key] = position
                logger.info(f"New long position: {position_key} at {position.entry_price}")
            else:
                # Short position
                position = Position(
                    exchange=order.exchange,
                    trading_pair=order.trading_pair,
                    side=PositionSide.SHORT,
                    entry_price=order.average_fill_price,
                    quantity=order.filled_quantity,
                    strategy_id=self.id
                )
                self.positions[position_key] = position
                logger.info(f"New short position: {position_key} at {position.entry_price}")
    
    def _calculate_pnl(self, position: Position, order: Order) -> float:
        """
        Calculate realized profit/loss for a position.
        
        Args:
            position: Position
            order: Order that affects the position
            
        Returns:
            Realized profit/loss
        """
        if position.side == PositionSide.LONG:
            # For long positions, sell orders realize profit/loss
            if order.side == OrderSide.SELL:
                return (order.average_fill_price - position.entry_price) * order.filled_quantity
        else:
            # For short positions, buy orders realize profit/loss
            if order.side == OrderSide.BUY:
                return (position.entry_price - order.average_fill_price) * order.filled_quantity
        
        return 0.0
    
    def calculate_position_size(self, trading_pair: str, exchange: str, 
                               available_capital: float, volatility: float) -> float:
        """
        Calculate appropriate position size based on risk parameters.
        
        Args:
            trading_pair: Trading pair
            exchange: Exchange name
            available_capital: Available capital
            volatility: Current volatility measure
            
        Returns:
            Recommended position size
        """
        # Get risk parameters
        risk_per_trade = self.risk_parameters.get('risk_per_trade', 0.02)  # Default 2% risk per trade
        
        # Calculate maximum capital at risk
        max_capital_at_risk = available_capital * risk_per_trade
        
        # Adjust based on volatility
        if volatility > 0:
            # Inverse relationship with volatility - higher volatility means smaller position
            position_size = max_capital_at_risk / volatility
        else:
            position_size = 0
            
        return position_size
    
    def calculate_volatility(self, market_data_list: List[MarketData]) -> float:
        """
        Calculate volatility from market data.
        
        Args:
            market_data_list: List of market data points
            
        Returns:
            Volatility measure
        """
        if len(market_data_list) < 2:
            return 0.0
            
        # Calculate daily volatility using standard deviation of returns
        prices = [data.close_price for data in market_data_list]
        returns = [(prices[i] / prices[i-1]) - 1 for i in range(1, len(prices))]
        
        return statistics.stdev(returns) if returns else 0.0


class MovingAverageCrossoverStrategy(StrategyBase):
    """Moving Average Crossover strategy implementation."""
    
    def __init__(self, strategy_config: Strategy, data_collector: DataCollector):
        """Initialize Moving Average Crossover strategy."""
        super().__init__(strategy_config, data_collector)
        
        # Strategy-specific parameters
        self.short_window = self.parameters.get('short_window', 50)
        self.long_window = self.parameters.get('long_window', 200)
        self.volatility_scaling = self.parameters.get('volatility_scaling', True)
        
        # Internal state for MA calculations
        self.short_ma = {}  # Dict to store short MA for each pair
        self.long_ma = {}   # Dict to store long MA for each pair
        self.market_data_history = {}  # Dict to store market data history
    
    async def process_market_data(self, market_data: MarketData) -> None:
        """Process new market data for MA strategy."""
        pair_key = f"{market_data.exchange}:{market_data.trading_pair}"
        
        # Store market data
        if pair_key not in self.market_data_history:
            self.market_data_history[pair_key] = []
        
        self.market_data_history[pair_key].append(market_data)
        
        # Keep only necessary data points
        max_window = max(self.short_window, self.long_window)
        if len(self.market_data_history[pair_key]) > max_window + 10:  # Keep a few extra for calculations
            self.market_data_history[pair_key] = self.market_data_history[pair_key][-max_window-10:]
        
        # Update moving averages
        if len(self.market_data_history[pair_key]) >= self.short_window:
            short_data = self.market_data_history[pair_key][-self.short_window:]
            self.short_ma[pair_key] = sum(data.close_price for data in short_data) / self.short_window
        
        if len(self.market_data_history[pair_key]) >= self.long_window:
            long_data = self.market_data_history[pair_key][-self.long_window:]
            self.long_ma[pair_key] = sum(data.close_price for data in long_data) / self.long_window
    
    async def generate_signals(self) -> List[Signal]:
        """Generate trading signals for MA strategy."""
        signals = []
        
        for pair_key in self.market_data_history:
            if pair_key not in self.short_ma or pair_key not in self.long_ma:
                continue
                
            exchange, trading_pair = pair_key.split(':')
            
            # Get previous moving averages (if available)
            prev_short_ma = None
            prev_long_ma = None
            
            if len(self.market_data_history[pair_key]) > self.short_window:
                prev_short_data = self.market_data_history[pair_key][-self.short_window-1:-1]
                prev_short_ma = sum(data.close_price for data in prev_short_data) / self.short_window
            
            if len(self.market_data_history[pair_key]) > self.long_window:
                prev_long_data = self.market_data_history[pair_key][-self.long_window-1:-1]
                prev_long_ma = sum(data.close_price for data in prev_long_data) / self.long_window
            
            # Current moving averages
            current_short_ma = self.short_ma[pair_key]
            current_long_ma = self.long_ma[pair_key]
            
            # Check for crossover
            current_position = None
            if pair_key in self.positions:
                current_position = self.positions[pair_key].side
            
            # Only generate signals if we have previous MAs
            if prev_short_ma is not None and prev_long_ma is not None:
                # Bullish crossover (short MA crosses above long MA)
                if prev_short_ma <= prev_long_ma and current_short_ma > current_long_ma:
                    if current_position != PositionSide.LONG:
                        # Calculate position size
                        volatility = self.calculate_volatility(self.market_data_history[pair_key])
                        position_size = self.calculate_position_size(
                            trading_pair, exchange, 10000, volatility  # Assuming 10000 available capital
                        )
                        
                        signal = Signal(
                            strategy_id=self.id,
                            trading_pair=trading_pair,
                            exchange=exchange,
                            signal_type=SignalType.ENTRY,
                            direction=PositionSide.LONG,
                            strength=1.0,
                            price=self.market_data_history[pair_key][-1].close_price,
                            quantity=position_size,
                            timestamp=datetime.now(),
                            expiration=datetime.now() + timedelta(hours=1),
                            metadata={"crossover_type": "bullish"}
                        )
                        signals.append(signal)
                        logger.info(f"Generated bullish signal for {pair_key}")
                
                # Bearish crossover (short MA crosses below long MA)
                elif prev_short_ma >= prev_long_ma and current_short_ma < current_long_ma:
                    if current_position != PositionSide.SHORT:
                        # Calculate position size
                        volatility = self.calculate_volatility(self.market_data_history[pair_key])
                        position_size = self.calculate_position_size(
                            trading_pair, exchange, 10000, volatility  # Assuming 10000 available capital
                        )
                        
                        signal = Signal(
                            strategy_id=self.id,
                            trading_pair=trading_pair,
                            exchange=exchange,
                            signal_type=SignalType.ENTRY,
                            direction=PositionSide.SHORT,
                            strength=1.0,
                            price=self.market_data_history[pair_key][-1].close_price,
                            quantity=position_size,
                            timestamp=datetime.now(),
                            expiration=datetime.now() + timedelta(hours=1),
                            metadata={"crossover_type": "bearish"}
                        )
                        signals.append(signal)
                        logger.info(f"Generated bearish signal for {pair_key}")
        
        return signals


class ArbitrageStrategy(StrategyBase):
    """Arbitrage strategy implementation."""
    
    def __init__(self, strategy_config: Strategy, data_collector: DataCollector):
        """Initialize Arbitrage strategy."""
        super().__init__(strategy_config, data_collector)
        
        # Strategy-specific parameters
        self.min_profit_threshold = self.parameters.get('min_profit_threshold', 0.01)  # 1% minimum profit
        self.max_position_size = self.parameters.get('max_position_size', 0.2)  # 20% of available balance
        self.execution_delay = self.parameters.get('execution_delay', 5)  # seconds
        
        # Internal state
        self.market_prices = {}  # Dict to store current prices across exchanges
        self.fee_rates = {}      # Dict to store fee rates for exchanges
        
        # Initialize fee rates
        for exchange in self.target_exchanges:
            self.fee_rates[exchange] = 0.001  # Default 0.1% fee
    
    async def process_market_data(self, market_data: MarketData) -> None:
        """Process new market data for arbitrage strategy."""
        key = f"{market_data.exchange}:{market_data.trading_pair}"
        self.market_prices[key] = {
            'bid': market_data.bid_price,
            'ask': market_data.ask_price,
            'timestamp': market_data.timestamp
        }
    
    async def generate_signals(self) -> List[Signal]:
        """Generate trading signals for arbitrage strategy."""
        signals = []
        
        # Group prices by trading pair
        pair_prices = {}
        for key, price_data in self.market_prices.items():
            exchange, pair = key.split(':')
            if pair not in pair_prices:
                pair_prices[pair] = {}
            pair_prices[pair][exchange] = price_data
        
        # Look for arbitrage opportunities
        for pair, exchanges in pair_prices.items():
            if len(exchanges) < 2:
                continue
            
            # Find best bid and ask across exchanges
            best_bid = {'exchange': None, 'price': 0}
            best_ask = {'exchange': None, 'price': float('inf')}
            
            for exchange, price_data in exchanges.items():
                if price_data.get('bid', 0) > best_bid['price']:
                    best_bid = {'exchange': exchange, 'price': price_data.get('bid', 0)}
                if price_data.get('ask', float('inf')) < best_ask['price']:
                    best_ask = {'exchange': exchange, 'price': price_data.get('ask', float('inf'))}
            
            # Calculate potential profit
            if best_bid['exchange'] and best_ask['exchange'] and best_bid['exchange'] != best_ask['exchange']:
                spread = best_bid['price'] - best_ask['price']
                spread_percentage = spread / best_ask['price'] if best_ask['price'] > 0 else 0
                
                # Account for fees
                buy_fee = self.fee_rates.get(best_ask['exchange'], 0.001)  # Default 0.1%
                sell_fee = self.fee_rates.get(best_bid['exchange'], 0.001)  # Default 0.1%
                total_fee_percentage = buy_fee + sell_fee
                
                net_profit_percentage = spread_percentage - total_fee_percentage
                
                # Check if profitable after fees
                if net_profit_percentage > self.min_profit_threshold:
                    # Calculate position size based on profit potential
                    position_size = self.max_position_size * min(1.0, net_profit_percentage * 10)
                    
                    # Generate buy signal
                    buy_signal = Signal(
                        strategy_id=self.id,
                        trading_pair=pair,
                        exchange=best_ask['exchange'],
                        signal_type=SignalType.ENTRY,
                        direction=PositionSide.LONG,
                        strength=min(1.0, net_profit_percentage * 10),  # Scale strength by profit
                        price=best_ask['price'],
                        quantity=position_size * 10000,  # Assuming 10000 available capital
                        timestamp=datetime.now(),
                        expiration=datetime.now() + timedelta(seconds=self.execution_delay),
                        metadata={
                            "arbitrage_type": "cross_exchange",
                            "sell_exchange": best_bid['exchange'],
                            "sell_price": best_bid['price'],
                            "expected_profit": net_profit_percentage
                        }
                    )
                    signals.append(buy_signal)
                    
                    # Generate sell signal
                    sell_signal = Signal(
                        strategy_id=self.id,
                        trading_pair=pair,
                        exchange=best_bid['exchange'],
                        signal_type=SignalType.EXIT,
                        direction=PositionSide.LONG,
                        strength=min(1.0, net_profit_percentage * 10),  # Scale strength by profit
                        price=best_bid['price'],
                        quantity=position_size * 10000,  # Assuming 10000 available capital
                        timestamp=datetime.now(),
                        expiration=datetime.now() + timedelta(seconds=self.execution_delay),
                        metadata={
                            "arbitrage_type": "cross_exchange",
                            "buy_exchange": best_ask['exchange'],
                            "buy_price": best_ask['price'],
                            "expected_profit": net_profit_percentage
                        }
                    )
                    signals.append(sell_signal)
                    
                    logger.info(f"Arbitrage opportunity: Buy {pair} on {best_ask['exchange']} at {best_ask['price']}, "
                               f"Sell on {best_bid['exchange']} at {best_bid['price']}, "
                               f"Profit: {net_profit_percentage:.2f}%")
        
        return signals


class StrategyFactory:
    """Factory for creating strategy instances."""
    
    @staticmethod
    def create_strategy(strategy_config: Strategy, data_collector: DataCollector) -> StrategyBase:
        """
        Create a strategy instance based on type and configuration.
        
        Args:
            strategy_config: Strategy configuration
            data_collector: Data collector instance
            
        Returns:
            Strategy instance
        """
        if strategy_config.type == StrategyType.TREND_FOLLOWING:
            return MovingAverageCrossoverStrategy(strategy_config, data_collector)
        elif strategy_config.type == StrategyType.ARBITRAGE:
            return ArbitrageStrategy(strategy_config, data_collector)
        else:
            raise ValueError(f"Unsupported strategy type: {strategy_config.type}")


class StrategyManager:
    """Manages multiple trading strategies."""
    
    def __init__(self, data_collector: DataCollector):
        """
        Initialize the strategy manager.
        
        Args:
            data_collector: Data collector instance
        """
        self.data_collector = data_collector
        self.strategies = {}  # Dict of strategy_id -> Strategy
    
    async def add_strategy(self, strategy_config: Strategy) -> None:
        """
        Add a new strategy to the manager.
        
        Args:
            strategy_config: Strategy configuration
        """
        strategy = StrategyFactory.create_strategy(strategy_config, self.data_collector)
        self.strategies[strategy_config.id] = strategy
        logger.info(f"Added strategy: {strategy_config.id} ({strategy_config.name})")
    
    async def remove_strategy(self, strategy_id: str) -> None:
        """
        Remove a strategy from the manager.
        
        Args:
            strategy_id: Strategy ID
        """
        if strategy_id in self.strategies:
            del self.strategies[strategy_id]
            logger.info(f"Removed strategy: {strategy_id}")
    
    async def process_market_data(self, market_data: MarketData) -> None:
        """
        Process market data through all active strategies.
        
        Args:
            market_data: Market data
        """
        for strategy in self.strategies.values():
            if strategy.status == "ACTIVE" and market_data.exchange in strategy.target_exchanges and market_data.trading_pair in strategy.target_pairs:
                await strategy.process_market_data(market_data)
    
    async def generate_signals(self) -> List[Signal]:
        """
        Generate signals from all active strategies.
        
        Returns:
            List of signals
        """
        all_signals = []
        for strategy in self.strategies.values():
            if strategy.status == "ACTIVE":
                signals = await strategy.generate_signals()
                all_signals.extend(signals)
        return all_signals
    
    async def on_order_update(self, order: Order) -> None:
        """
        Propagate order updates to the relevant strategy.
        
        Args:
            order: Updated order
        """
        if order.strategy_id and order.strategy_id in self.strategies:
            await self.strategies[order.strategy_id].on_order_update(order)
    
    async def on_trade(self, trade: Trade) -> None:
        """
        Propagate trade notifications to the relevant strategy.
        
        Args:
            trade: Completed trade
        """
        if trade.strategy_id and trade.strategy_id in self.strategies:
            await self.strategies[trade.strategy_id].on_trade(trade)
