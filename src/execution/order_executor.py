"""
Order execution module for cryptocurrency trading bot.
This module handles the execution of trading signals by creating and managing orders.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from ..models.base_models import (
    Order, OrderSide, OrderStatus, OrderType, Position, PositionSide, Signal, SignalType, Trade
)
from ..exchange.exchange_interface import ExchangeInterface
from ..data.data_collector import DataCollector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OrderExecutor:
    """
    Handles the execution of trading signals by creating and managing orders.
    """
    
    def __init__(self, exchanges: Dict[str, ExchangeInterface], data_collector: DataCollector):
        """
        Initialize the order executor.
        
        Args:
            exchanges: Dictionary mapping exchange names to exchange interfaces
            data_collector: Data collector instance
        """
        self.exchanges = exchanges
        self.data_collector = data_collector
        self.open_orders = {}  # Dict to track open orders
        self.positions = {}    # Dict to track open positions
        self.order_history = []  # List to track order history
        self.trade_history = []  # List to track trade history
    
    async def execute_signal(self, signal: Signal) -> Optional[Order]:
        """
        Execute a trading signal by creating an order.
        
        Args:
            signal: Trading signal
            
        Returns:
            Created order or None if execution failed
        """
        # Check if signal is expired
        if signal.expiration and datetime.now() > signal.expiration:
            logger.warning(f"Signal expired: {signal.id}")
            return None
        
        # Get exchange interface
        exchange = self.exchanges.get(signal.exchange)
        if not exchange:
            logger.error(f"Exchange not found: {signal.exchange}")
            return None
        
        # Determine order type and side
        order_type = OrderType.MARKET  # Default to market order
        
        if signal.signal_type == SignalType.ENTRY:
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
                quantity=signal.quantity,
                price=signal.price if order_type == OrderType.LIMIT else None
            )
            
            # Add strategy ID to order
            order.strategy_id = signal.strategy_id
            
            # Track order
            self.open_orders[order.id] = order
            self.order_history.append(order)
            
            logger.info(f"Order created: {order.id} for {signal.trading_pair} on {signal.exchange}")
            
            return order
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            return None
    
    async def execute_signals(self, signals: List[Signal]) -> List[Order]:
        """
        Execute multiple trading signals.
        
        Args:
            signals: List of trading signals
            
        Returns:
            List of created orders
        """
        orders = []
        for signal in signals:
            order = await self.execute_signal(signal)
            if order:
                orders.append(order)
        return orders
    
    async def cancel_order(self, order_id: str, exchange_name: str, trading_pair: str) -> bool:
        """
        Cancel an open order.
        
        Args:
            order_id: Order ID
            exchange_name: Exchange name
            trading_pair: Trading pair
            
        Returns:
            True if cancellation was successful, False otherwise
        """
        # Get exchange interface
        exchange = self.exchanges.get(exchange_name)
        if not exchange:
            logger.error(f"Exchange not found: {exchange_name}")
            return False
        
        # Cancel order
        try:
            result = await exchange.cancel_order(order_id, trading_pair)
            
            if result:
                # Update order status
                if order_id in self.open_orders:
                    self.open_orders[order_id].status = OrderStatus.CANCELED
                    self.open_orders[order_id].updated_at = datetime.now()
                    logger.info(f"Order canceled: {order_id}")
                
                return True
            else:
                logger.warning(f"Failed to cancel order: {order_id}")
                return False
        except Exception as e:
            logger.error(f"Error canceling order: {e}")
            return False
    
    async def update_order_status(self, order_id: str, exchange_name: str, trading_pair: str) -> Optional[Order]:
        """
        Update the status of an order.
        
        Args:
            order_id: Order ID
            exchange_name: Exchange name
            trading_pair: Trading pair
            
        Returns:
            Updated order or None if update failed
        """
        # Get exchange interface
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
                        await self._update_position(order)
                        
                        # Create trade record
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
                        self.trade_history.append(trade)
                        logger.info(f"Trade recorded: {trade.id} for {trade.trading_pair} on {trade.exchange}")
            
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
            if (position.side == PositionSide.LONG and order.side == OrderSide.BUY) or \
               (position.side == PositionSide.SHORT and order.side == OrderSide.SELL):
                # Calculate new average entry price
                total_value = (position.entry_price * position.quantity) + (order.average_fill_price * order.filled_quantity)
                total_quantity = position.quantity + order.filled_quantity
                new_entry_price = total_value / total_quantity if total_quantity > 0 else 0
                
                # Update position
                position.entry_price = new_entry_price
                position.quantity += order.filled_quantity
                position.last_update_time = datetime.now()
                logger.info(f"Position increased: {position_key} to {position.quantity} at {position.entry_price}")
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
                    entry_price=order.average_fill_price if order.average_fill_price else order.price,
                    quantity=order.filled_quantity,
                    strategy_id=order.strategy_id
                )
                self.positions[position_key] = position
                logger.info(f"New long position: {position_key} at {position.entry_price}")
            else:
                # Short position
                position = Position(
                    exchange=order.exchange,
                    trading_pair=order.trading_pair,
                    side=PositionSide.SHORT,
                    entry_price=order.average_fill_price if order.average_fill_price else order.price,
                    quantity=order.filled_quantity,
                    strategy_id=order.strategy_id
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
                return (order.average_fill_price - position.entry_price) * min(order.filled_quantity, position.quantity)
        else:
            # For short positions, buy orders realize profit/loss
            if order.side == OrderSide.BUY:
                return (position.entry_price - order.average_fill_price) * min(order.filled_quantity, position.quantity)
        
        return 0.0
    
    async def update_positions(self) -> None:
        """Update unrealized profit/loss for all positions."""
        for position_key, position in self.positions.items():
            exchange_name, trading_pair = position_key.split(':')
            
            # Get current price
            ticker = await self.data_collector.fetch_ticker(exchange_name, trading_pair)
            if ticker:
                # Update unrealized PnL
                if position.side == PositionSide.LONG:
                    position.unrealized_pnl = (ticker.close_price - position.entry_price) * position.quantity
                else:  # SHORT
                    position.unrealized_pnl = (position.entry_price - ticker.close_price) * position.quantity
                
                position.last_update_time = datetime.now()
    
    def get_position(self, exchange: str, trading_pair: str) -> Optional[Position]:
        """
        Get position for a trading pair on an exchange.
        
        Args:
            exchange: Exchange name
            trading_pair: Trading pair
            
        Returns:
            Position or None if not found
        """
        position_key = f"{exchange}:{trading_pair}"
        return self.positions.get(position_key)
    
    def get_open_orders(self, exchange: Optional[str] = None, trading_pair: Optional[str] = None) -> List[Order]:
        """
        Get open orders, optionally filtered by exchange and trading pair.
        
        Args:
            exchange: Optional exchange name filter
            trading_pair: Optional trading pair filter
            
        Returns:
            List of open orders
        """
        if not exchange and not trading_pair:
            return list(self.open_orders.values())
        
        filtered_orders = []
        for order in self.open_orders.values():
            if exchange and order.exchange != exchange:
                continue
            if trading_pair and order.trading_pair != trading_pair:
                continue
            filtered_orders.append(order)
        
        return filtered_orders
    
    def get_positions(self, exchange: Optional[str] = None, trading_pair: Optional[str] = None) -> List[Position]:
        """
        Get positions, optionally filtered by exchange and trading pair.
        
        Args:
            exchange: Optional exchange name filter
            trading_pair: Optional trading pair filter
            
        Returns:
            List of positions
        """
        if not exchange and not trading_pair:
            return list(self.positions.values())
        
        filtered_positions = []
        for position_key, position in self.positions.items():
            position_exchange, position_pair = position_key.split(':')
            if exchange and position_exchange != exchange:
                continue
            if trading_pair and position_pair != trading_pair:
                continue
            filtered_positions.append(position)
        
        return filtered_positions
    
    def get_order_history(self, limit: int = 100) -> List[Order]:
        """
        Get order history.
        
        Args:
            limit: Maximum number of orders to return
            
        Returns:
            List of historical orders
        """
        return self.order_history[-limit:]
    
    def get_trade_history(self, limit: int = 100) -> List[Trade]:
        """
        Get trade history.
        
        Args:
            limit: Maximum number of trades to return
            
        Returns:
            List of historical trades
        """
        return self.trade_history[-limit:]
