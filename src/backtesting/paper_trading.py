"""
Paper trading module for cryptocurrency trading bot.
This module simulates trading without using real funds.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Union

from ..models.base_models import (
    Order, OrderSide, OrderStatus, OrderType, Position, PositionSide, Signal, Trade,
    Exchange, ExchangeType
)
from ..data.data_collector import DataCollector
from ..exchange.exchange_interface import ExchangeInterface
from ..risk.risk_manager import RiskManager
from ..utils.monitoring import MonitoringSystem

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PaperTradingExchange(ExchangeInterface):
    """
    Paper trading exchange implementation that simulates real exchange behavior.
    """
    
    def __init__(self, exchange_config: Dict, data_collector: DataCollector):
        """
        Initialize the paper trading exchange.
        
        Args:
            exchange_config: Exchange configuration
            data_collector: Data collector instance for market data
        """
        # Create Exchange object from config
        exchange = Exchange(
            name=exchange_config['name'],
            exchange_type=ExchangeType.CEX,
            base_url="",
            websocket_url="",
            api_key=exchange_config.get('api_key', ''),
            api_secret=exchange_config.get('api_secret', ''),
            trading_pairs=exchange_config.get('trading_pairs', [])
        )
        super().__init__(exchange)
        
        self.data_collector = data_collector
        self.balances = exchange_config.get('initial_balances', {})
        self.open_orders = {}  # Dict to track open orders
        self.positions = {}    # Dict to track open positions
        self.order_history = []  # List to track order history
        self.trade_history = []  # List to track trade history
        self.fees = exchange_config.get('fees', {
            'maker': 0.001,  # 0.1% maker fee
            'taker': 0.001   # 0.1% taker fee
        })
        self.slippage = exchange_config.get('slippage', 0.001)  # 0.1% slippage
        
        # Ensure we have a minimum balance for quote currencies
        for pair in self.exchange.trading_pairs:
            quote_currency = pair.split('/')[1]
            if quote_currency not in self.balances:
                self.balances[quote_currency] = 10000.0  # Default 10,000 units
    
    async def fetch_market_data(self, trading_pair: str, interval: str = '1h', limit: int = 100) -> List:
        """
        Fetch historical market data from the real exchange via data collector.
        
        Args:
            trading_pair: Trading pair symbol
            interval: Candlestick interval
            limit: Number of candlesticks to fetch
            
        Returns:
            List of market data objects
        """
        return await self.data_collector.fetch_historical_data(
            self.exchange.name, trading_pair, interval, limit
        )
    
    async def fetch_ticker(self, trading_pair: str) -> Optional[Dict]:
        """
        Fetch current ticker data from the real exchange via data collector.
        
        Args:
            trading_pair: Trading pair symbol
            
        Returns:
            Ticker data
        """
        return await self.data_collector.fetch_ticker(self.exchange.name, trading_pair)
    
    async def fetch_order_book(self, trading_pair: str, limit: int = 20) -> Optional[Dict]:
        """
        Fetch order book from the real exchange via data collector.
        
        Args:
            trading_pair: Trading pair symbol
            limit: Depth of the order book to fetch
            
        Returns:
            Order book data
        """
        return await self.data_collector.fetch_order_book(self.exchange.name, trading_pair, limit)
    
    async def create_order(self, trading_pair: str, order_type: OrderType, 
                          side: OrderSide, quantity: float, price: Optional[float] = None) -> Order:
        """
        Create a simulated order.
        
        Args:
            trading_pair: Trading pair symbol
            order_type: Order type (MARKET, LIMIT)
            side: Order side (BUY, SELL)
            quantity: Order quantity
            price: Order price (required for LIMIT orders)
            
        Returns:
            Created order
        """
        # Generate order ID
        order_id = str(uuid.uuid4())
        
        # Get current market price
        ticker = await self.fetch_ticker(trading_pair)
        if not ticker:
            raise ValueError(f"Failed to fetch ticker for {trading_pair}")
        
        current_price = ticker.close_price
        
        # Determine execution price with slippage
        if order_type == OrderType.MARKET:
            if side == OrderSide.BUY:
                execution_price = current_price * (1 + self.slippage)  # Higher price for buys
            else:
                execution_price = current_price * (1 - self.slippage)  # Lower price for sells
        else:  # LIMIT
            if not price:
                raise ValueError("Price is required for LIMIT orders")
            execution_price = price
        
        # Check if we have enough balance
        base_currency, quote_currency = trading_pair.split('/')
        
        if side == OrderSide.BUY:
            required_balance = quantity * execution_price
            if quote_currency not in self.balances or self.balances[quote_currency] < required_balance:
                raise ValueError(f"Insufficient balance: {quote_currency}")
        else:  # SELL
            if base_currency not in self.balances or self.balances[base_currency] < quantity:
                raise ValueError(f"Insufficient balance: {base_currency}")
        
        # Create order
        order = Order(
            id=order_id,
            exchange=self.exchange.name,
            trading_pair=trading_pair,
            order_type=order_type,
            side=side,
            quantity=quantity,
            price=execution_price,
            status=OrderStatus.OPEN,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # For market orders, execute immediately
        if order_type == OrderType.MARKET:
            await self._execute_order(order)
        else:
            # For limit orders, store in open orders
            self.open_orders[order_id] = order
        
        # Add to order history
        self.order_history.append(order)
        
        logger.info(f"Created order: {order_id} for {trading_pair} ({side.value}) at {execution_price}")
        
        return order
    
    async def cancel_order(self, order_id: str, trading_pair: str) -> bool:
        """
        Cancel an open order.
        
        Args:
            order_id: Order ID
            trading_pair: Trading pair symbol
            
        Returns:
            True if cancellation was successful, False otherwise
        """
        if order_id in self.open_orders:
            order = self.open_orders[order_id]
            order.status = OrderStatus.CANCELED
            order.updated_at = datetime.now()
            
            # Remove from open orders
            del self.open_orders[order_id]
            
            logger.info(f"Canceled order: {order_id}")
            
            return True
        else:
            logger.warning(f"Order not found: {order_id}")
            return False
    
    async def fetch_order(self, order_id: str, trading_pair: str) -> Optional[Order]:
        """
        Fetch an order by ID.
        
        Args:
            order_id: Order ID
            trading_pair: Trading pair symbol
            
        Returns:
            Order or None if not found
        """
        # Check open orders
        if order_id in self.open_orders:
            return self.open_orders[order_id]
        
        # Check order history
        for order in self.order_history:
            if order.id == order_id:
                return order
        
        return None
    
    async def fetch_open_orders(self, trading_pair: Optional[str] = None) -> List[Order]:
        """
        Fetch open orders.
        
        Args:
            trading_pair: Optional trading pair filter
            
        Returns:
            List of open orders
        """
        if not trading_pair:
            return list(self.open_orders.values())
        
        return [order for order in self.open_orders.values() if order.trading_pair == trading_pair]
    
    async def fetch_balance(self) -> Dict[str, float]:
        """
        Fetch account balances.
        
        Returns:
            Dictionary mapping currency symbols to balances
        """
        return self.balances
    
    async def fetch_trades(self, trading_pair: str, limit: int = 50) -> List[Trade]:
        """
        Fetch recent trades for a trading pair.
        
        Args:
            trading_pair: Trading pair symbol
            limit: Number of trades to fetch
            
        Returns:
            List of Trade objects
        """
        # Filter trades by trading pair and limit the number of results
        trades = [trade for trade in self.trade_history if trade.trading_pair == trading_pair]
        return trades[-limit:] if trades else []
    
    async def _execute_order(self, order: Order) -> None:
        """
        Execute an order (internal method).
        
        Args:
            order: Order to execute
        """
        base_currency, quote_currency = order.trading_pair.split('/')
        
        # Calculate fee
        fee_rate = self.fees['taker']
        fee_currency = quote_currency if order.side == OrderSide.BUY else base_currency
        fee_amount = order.quantity * order.price * fee_rate if order.side == OrderSide.BUY else order.quantity * fee_rate
        
        # Update balances
        if order.side == OrderSide.BUY:
            # Deduct quote currency
            total_cost = order.quantity * order.price
            self.balances[quote_currency] -= total_cost
            
            # Add base currency
            if base_currency not in self.balances:
                self.balances[base_currency] = 0
            self.balances[base_currency] += order.quantity
        else:  # SELL
            # Deduct base currency
            self.balances[base_currency] -= order.quantity
            
            # Add quote currency
            total_proceeds = order.quantity * order.price
            if quote_currency not in self.balances:
                self.balances[quote_currency] = 0
            self.balances[quote_currency] += total_proceeds
        
        # Update order status
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.average_fill_price = order.price
        order.updated_at = datetime.now()
        order.fees = {fee_currency: fee_amount}
        
        # Create trade record
        trade = Trade(
            id=str(uuid.uuid4()),
            order_id=order.id,
            exchange=order.exchange,
            trading_pair=order.trading_pair,
            side=order.side,
            quantity=order.quantity,
            price=order.price,
            fee=order.fees,
            timestamp=datetime.now(),
            strategy_id=order.strategy_id
        )
        
        self.trade_history.append(trade)
        
        # Update position
        position_key = f"{order.trading_pair}"
        
        if order.side == OrderSide.BUY:
            # Long position
            if position_key not in self.positions:
                self.positions[position_key] = Position(
                    exchange=order.exchange,
                    trading_pair=order.trading_pair,
                    side=PositionSide.LONG,
                    entry_price=order.price,
                    quantity=order.quantity,
                    strategy_id=order.strategy_id
                )
            else:
                position = self.positions[position_key]
                
                # If same side, increase position
                if position.side == PositionSide.LONG:
                    # Calculate new average entry price
                    total_value = (position.entry_price * position.quantity) + (order.price * order.quantity)
                    total_quantity = position.quantity + order.quantity
                    new_entry_price = total_value / total_quantity if total_quantity > 0 else 0
                    
                    # Update position
                    position.entry_price = new_entry_price
                    position.quantity += order.quantity
                    position.last_update_time = datetime.now()
                else:
                    # Opposite side, reduce position
                    if order.quantity >= position.quantity:
                        # Position closed
                        del self.positions[position_key]
                    else:
                        # Position reduced
                        position.quantity -= order.quantity
                        position.last_update_time = datetime.now()
        else:  # SELL
            # Short position
            if position_key not in self.positions:
                self.positions[position_key] = Position(
                    exchange=order.exchange,
                    trading_pair=order.trading_pair,
                    side=PositionSide.SHORT,
                    entry_price=order.price,
                    quantity=order.quantity,
                    strategy_id=order.strategy_id
                )
            else:
                position = self.positions[position_key]
                
                # If same side, increase position
                if position.side == PositionSide.SHORT:
                    # Calculate new average entry price
                    total_value = (position.entry_price * position.quantity) + (order.price * order.quantity)
                    total_quantity = position.quantity + order.quantity
                    new_entry_price = total_value / total_quantity if total_quantity > 0 else 0
                    
                    # Update position
                    position.entry_price = new_entry_price
                    position.quantity += order.quantity
                    position.last_update_time = datetime.now()
                else:
                    # Opposite side, reduce position
                    if order.quantity >= position.quantity:
                        # Position closed
                        del self.positions[position_key]
                    else:
                        # Position reduced
                        position.quantity -= order.quantity
                        position.last_update_time = datetime.now()
        
        logger.info(f"Executed order: {order.id} for {order.trading_pair} ({order.side.value}) at {order.price}")
    
    async def process_limit_orders(self) -> None:
        """Process open limit orders against current market prices."""
        for order_id, order in list(self.open_orders.items()):
            # Get current market price
            ticker = await self.fetch_ticker(order.trading_pair)
            if not ticker:
                continue
            
            current_price = ticker.close_price
            
            # Check if limit order should be executed
            if order.side == OrderSide.BUY and current_price <= order.price:
                await self._execute_order(order)
                del self.open_orders[order_id]
            elif order.side == OrderSide.SELL and current_price >= order.price:
                await self._execute_order(order)
                del self.open_orders[order_id]
    
    def get_total_balance_in_usd(self) -> float:
        """
        Calculate total account balance in USD equivalent.
        
        Returns:
            Total balance in USD
        """
        # This is a simplified implementation
        # A real implementation would convert all balances to USD using current exchange rates
        return sum(self.balances.values())


class PaperTradingSystem:
    """
    Paper trading system that simulates trading without using real funds.
    """
    
    def __init__(self, config: Dict, data_collector: DataCollector, risk_manager: RiskManager, 
                monitoring_system: MonitoringSystem):
        """
        Initialize the paper trading system.
        
        Args:
            config: Paper trading configuration
            data_collector: Data collector instance
            risk_manager: Risk manager instance
            monitoring_system: Monitoring system instance
        """
        self.config = config
        self.data_collector = data_collector
        self.risk_manager = risk_manager
        self.monitoring_system = monitoring_system
        
        # Create paper trading exchanges
        self.exchanges = {}
        for exchange_name, exchange_config in config.get('exchanges', {}).items():
            self.exchanges[exchange_name] = PaperTradingExchange(
                {**exchange_config, 'name': exchange_name},
                data_collector
            )
        
        self.open_orders = {}  # Dict to track open orders across exchanges
        self.positions = {}    # Dict to track open positions across exchanges
        
        # Initialize with starting balance
        self.starting_balance = self._calculate_total_balance()
        self.current_balance = self.starting_balance
        
        # Update monitoring system with starting balance
        self.monitoring_system.update_balance(self.starting_balance)
    
    async def execute_signal(self, signal: Signal) -> Optional[Order]:
        """
        Execute a trading signal by creating an order.
        
        Args:
            signal: Trading signal
            
        Returns:
            Created order or None if execution failed
        """
        # Get exchange
        exchange = self.exchanges.get(signal.exchange)
        if not exchange:
            logger.error(f"Exchange not found: {signal.exchange}")
            return None
        
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
        
        if not is_allowed:
            logger.warning(f"Signal rejected by risk manager: {signal.id}")
            return None
        
        # Determine order type and side
        order_type = OrderType.MARKET  # Default to market order
        
        if signal.signal_type == "ENTRY":
            if signal.direction == PositionSide.LONG:
                order_side = OrderSide.BUY
            else:  # SHORT
                order_side = OrderSide.SELL
        else:  # EXIT
            if signal.direction == PositionSide.LONG:
                order_side = OrderSide.SELL
            else:  # SHORT
                order_side = OrderSide.BUY
        
        # Create order
        try:
            order = await exchange.create_order(
                trading_pair=signal.trading_pair,
                order_type=order_type,
                side=order_side,
                quantity=adjusted_size,
                price=signal.price if order_type == OrderType.LIMIT else None
            )
            
            # Add strategy ID to order
            order.strategy_id = signal.strategy_id
            
            # Track order
            self.open_orders[order.id] = order
            
            # Monitor order
            self.monitoring_system.monitor_order(order)
            
            # Update balance
            self.current_balance = self._calculate_total_balance()
            self.monitoring_system.update_balance(self.current_balance)
            
            logger.info(f"Order created: {order.id} for {signal.trading_pair} on {signal.exchange}")
            
            return order
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            return None
    
    async def update_order_status(self, order_id: str, exchange_name: str, trading_pair: str) -> Optional[Order]:
        """
        Update the status of an order.
        
        Args:
            order_id: Order ID
            exchange_name: Exchange name
            trading_pair: Trading pair symbol
            
        Returns:
            Updated order or None if update failed
        """
        # Get exchange
        exchange = self.exchanges.get(exchange_name)
        if not exchange:
            logger.error(f"Exchange not found: {exchange_name}")
            return None
        
        # Fetch order
        try:
            order = await exchange.fetch_order(order_id, trading_pair)
            
            # Update tracked order
            if order_id in self.open_orders:
                self.open_orders[order_id] = order
                
                # If order is filled or canceled, remove from open orders
                if order.status in [OrderStatus.FILLED, OrderStatus.CANCELED, OrderStatus.REJECTED, OrderStatus.EXPIRED]:
                    del self.open_orders[order_id]
                    
                    # If order is filled, update position
                    if order.status == OrderStatus.FILLED:
                        # Update balance
                        self.current_balance = self._calculate_total_balance()
                        self.monitoring_system.update_balance(self.current_balance)
                        
                        # Add trade to monitoring system
                        trade = Trade(
                            id=str(uuid.uuid4()),
                            order_id=order.id,
                            exchange=order.exchange,
                            trading_pair=order.trading_pair,
                            side=order.side,
                            quantity=order.filled_quantity,
                            price=order.average_fill_price if order.average_fill_price else order.price,
                            fee=order.fees,
                            timestamp=datetime.now(),
                            strategy_id=order.strategy_id
                        )
                        self.monitoring_system.add_trade(trade)
            
            return order
        except Exception as e:
            logger.error(f"Error updating order status: {e}")
            return None
    
    async def update_all_orders(self) -> None:
        """Update the status of all open orders."""
        order_ids = list(self.open_orders.keys())
        for order_id in order_ids:
            order = self.open_orders[order_id]
            await self.update_order_status(order_id, order.exchange, order.trading_pair)
    
    async def process_limit_orders(self) -> None:
        """Process open limit orders on all exchanges."""
        for exchange in self.exchanges.values():
            await exchange.process_limit_orders()
    
    async def update_positions(self) -> None:
        """Update all positions with current market prices."""
        for exchange_name, exchange in self.exchanges.items():
            for position_key, position in exchange.positions.items():
                # Get current price
                ticker = await self.data_collector.fetch_ticker(exchange_name, position.trading_pair)
                if ticker:
                    # Monitor position
                    self.monitoring_system.monitor_position(position, ticker.close_price)
                    
                    # Update position risk
                    position_id = f"{exchange_name}:{position.trading_pair}"
                    current_stop = position.stop_loss_price
                    
                    new_stop = self.risk_manager.update_position_risk(
                        position_id, ticker.close_price, current_stop
                    )
                    
                    if new_stop and new_stop != current_stop:
                        position.stop_loss_price = new_stop
                        logger.info(f"Updated stop-loss for {position_id}: {new_stop}")
                    
                    # Check if stop-loss is triggered
                    if position.stop_loss_price:
                        if (position.side == PositionSide.LONG and ticker.close_price <= position.stop_loss_price) or \
                           (position.side == PositionSide.SHORT and ticker.close_price >= position.stop_loss_price):
                            # Create exit signal
                            signal = Signal(
                                id=str(uuid.uuid4()),
                                strategy_id=position.strategy_id,
                                trading_pair=position.trading_pair,
                                exchange=exchange_name,
                                signal_type="EXIT",
                                direction=position.side,
                                strength=1.0,
                                price=ticker.close_price,
                                quantity=position.quantity,
                                timestamp=datetime.now(),
                                expiration=datetime.now() + timedelta(minutes=5),
                                metadata={"reason": "stop_loss"}
                            )
                            
                            # Execute signal
                            await self.execute_signal(signal)
                            
                            logger.warning(f"Stop-loss triggered for {position_id} at {ticker.close_price}")
    
    def _calculate_total_balance(self) -> float:
        """
        Calculate total balance across all exchanges.
        
        Returns:
            Total balance in USD
        """
        total = 0.0
        for exchange in self.exchanges.values():
            total += exchange.get_total_balance_in_usd()
        return total
    
    async def run_paper_trading(self, signals_queue, update_interval: int = 10) -> None:
        """
        Run the paper trading system.
        
        Args:
            signals_queue: Queue of trading signals
            update_interval: Update interval in seconds
        """
        logger.info("Starting paper trading system")
        
        while True:
            try:
                # Process signals
                while not signals_queue.empty():
                    signal = signals_queue.get_nowait()
                    await self.execute_signal(signal)
                
                # Update orders and positions
                await self.update_all_orders()
                await self.process_limit_orders()
                await self.update_positions()
                
                # Update balance
                self.current_balance = self._calculate_total_balance()
                self.monitoring_system.update_balance(self.current_balance)
                
                # Log current status
                logger.info(f"Paper trading status: Balance: {self.current_balance:.2f}, "
                           f"Open orders: {len(self.open_orders)}")
                
                await asyncio.sleep(update_interval)
            except Exception as e:
                logger.error(f"Error in paper trading loop: {e}")
                await asyncio.sleep(10)  # Wait a bit before retrying
