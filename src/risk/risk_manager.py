"""
Risk management module for cryptocurrency trading bot.
This module implements risk management features to protect capital and ensure sustainable trading.
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union

from ..models.base_models import (
    Order, OrderSide, OrderStatus, OrderType, Position, PositionSide, Signal, SignalType
)
from ..data.data_collector import DataCollector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PositionSizer:
    """Calculates appropriate position sizes based on risk parameters."""
    
    def __init__(self, config: Dict):
        """
        Initialize the position sizer.
        
        Args:
            config: Risk configuration parameters
        """
        self.risk_per_trade = config.get('risk_per_trade', 0.02)  # Default 2% risk per trade
        self.max_position_size = config.get('max_position_size', 0.2)  # Default 20% of capital
        self.volatility_scaling = config.get('volatility_scaling', True)
        self.target_volatility = config.get('target_volatility', 0.02)  # 2% daily volatility target
    
    def calculate_position_size(
        self,
        strategy_id: str,
        trading_pair: str,
        direction: PositionSide,
        available_capital: float,
        volatility: float
    ) -> float:
        """
        Calculate appropriate position size based on risk parameters.
        
        Args:
            strategy_id: Identifier for the strategy
            trading_pair: The trading pair (e.g., "BTC/USDT")
            direction: "LONG" or "SHORT"
            available_capital: Available capital for trading
            volatility: Current volatility measure (e.g., ATR or standard deviation)
            
        Returns:
            Recommended position size
        """
        # Calculate maximum capital at risk
        max_capital_at_risk = available_capital * self.risk_per_trade
        
        # Base position size (without volatility scaling)
        base_position_size = available_capital * self.max_position_size
        
        # Apply volatility scaling if enabled
        if self.volatility_scaling and volatility > 0:
            # Inverse relationship with volatility - higher volatility means smaller position
            volatility_scalar = self.target_volatility / volatility
            position_size = min(base_position_size, max_capital_at_risk / volatility)
        else:
            position_size = base_position_size
        
        # Ensure position size doesn't exceed maximum
        position_size = min(position_size, available_capital * self.max_position_size)
        
        logger.info(f"Calculated position size for {trading_pair}: {position_size} "
                   f"(volatility: {volatility:.4f}, risk: {self.risk_per_trade:.2f})")
        
        return position_size


class StopLossManager:
    """Manages stop-loss levels for open positions."""
    
    def __init__(self, config: Dict):
        """
        Initialize the stop-loss manager.
        
        Args:
            config: Risk configuration parameters
        """
        self.risk_multiplier = config.get('risk_multiplier', 2.0)  # Default 2x ATR
        self.trailing_stop_enabled = config.get('trailing_stop', {}).get('enabled', True)
        self.trailing_stop_percent = config.get('trailing_stop', {}).get('percent', 0.05)  # Default 5%
    
    def calculate_stop_loss(
        self,
        entry_price: float,
        direction: PositionSide,
        volatility: float
    ) -> float:
        """
        Calculate appropriate stop-loss level based on volatility.
        
        Args:
            entry_price: Position entry price
            direction: "LONG" or "SHORT"
            volatility: Current volatility measure (e.g., ATR)
            
        Returns:
            Stop-loss price level
        """
        if direction == PositionSide.LONG:
            stop_loss = entry_price - (volatility * self.risk_multiplier)
        else:  # SHORT
            stop_loss = entry_price + (volatility * self.risk_multiplier)
        
        logger.info(f"Calculated stop-loss for {direction.value} position at {entry_price}: {stop_loss} "
                   f"(volatility: {volatility:.4f}, multiplier: {self.risk_multiplier})")
        
        return stop_loss
    
    def update_trailing_stop(
        self,
        current_price: float,
        direction: PositionSide,
        current_stop: float
    ) -> float:
        """
        Update trailing stop-loss level based on price movement.
        
        Args:
            current_price: Current market price
            direction: "LONG" or "SHORT"
            current_stop: Current stop-loss level
            
        Returns:
            Updated stop-loss price level
        """
        if not self.trailing_stop_enabled:
            return current_stop
        
        if direction == PositionSide.LONG:
            trail_level = current_price * (1 - self.trailing_stop_percent)
            new_stop = max(current_stop, trail_level)
            
            if new_stop > current_stop:
                logger.info(f"Updated trailing stop for LONG position: {current_stop} -> {new_stop} "
                           f"(current price: {current_price})")
            
            return new_stop
        else:  # SHORT
            trail_level = current_price * (1 + self.trailing_stop_percent)
            new_stop = min(current_stop, trail_level)
            
            if new_stop < current_stop:
                logger.info(f"Updated trailing stop for SHORT position: {current_stop} -> {new_stop} "
                           f"(current price: {current_price})")
            
            return new_stop


class RiskExposureMonitor:
    """Tracks and limits overall risk exposure."""
    
    def __init__(self, config: Dict):
        """
        Initialize the risk exposure monitor.
        
        Args:
            config: Risk configuration parameters
        """
        self.max_total_exposure = config.get('max_exposure', 0.5)  # Default 50% max exposure
        self.correlation_threshold = config.get('correlation_threshold', 0.7)
        self.positions = {}  # Dict of position_id -> position details
        self.total_capital = 0.0
    
    def set_total_capital(self, capital: float) -> None:
        """
        Set the total capital available.
        
        Args:
            capital: Total capital amount
        """
        self.total_capital = capital
    
    def add_position(
        self,
        position_id: str,
        trading_pair: str,
        size: float,
        entry_price: float,
        direction: PositionSide
    ) -> None:
        """
        Add a new position to the monitor.
        
        Args:
            position_id: Position identifier
            trading_pair: Trading pair
            size: Position size
            entry_price: Entry price
            direction: Position direction
        """
        self.positions[position_id] = {
            'trading_pair': trading_pair,
            'size': size,
            'entry_price': entry_price,
            'direction': direction,
            'current_price': entry_price
        }
        
        logger.info(f"Added position to risk monitor: {position_id} ({trading_pair}, {direction.value}, {size})")
    
    def update_position(self, position_id: str, current_price: float) -> None:
        """
        Update a position with current market price.
        
        Args:
            position_id: Position identifier
            current_price: Current market price
        """
        if position_id in self.positions:
            self.positions[position_id]['current_price'] = current_price
    
    def remove_position(self, position_id: str) -> None:
        """
        Remove a closed position from the monitor.
        
        Args:
            position_id: Position identifier
        """
        if position_id in self.positions:
            logger.info(f"Removed position from risk monitor: {position_id}")
            del self.positions[position_id]
    
    def calculate_total_exposure(self) -> float:
        """
        Calculate total risk exposure as a percentage of capital.
        
        Returns:
            Total exposure as a percentage
        """
        if self.total_capital <= 0:
            return 0.0
        
        total_exposure = sum(
            pos['size'] * pos['current_price'] for pos in self.positions.values()
        )
        
        return total_exposure / self.total_capital if self.total_capital > 0 else 0.0
    
    def is_new_position_allowed(self, size: float, price: float) -> bool:
        """
        Check if a new position would exceed maximum exposure.
        
        Args:
            size: Position size
            price: Position price
            
        Returns:
            True if position is allowed, False otherwise
        """
        current_exposure = self.calculate_total_exposure()
        new_position_value = size * price
        new_exposure = current_exposure + (new_position_value / self.total_capital if self.total_capital > 0 else 0)
        
        allowed = new_exposure <= self.max_total_exposure
        
        if not allowed:
            logger.warning(f"New position rejected: would exceed max exposure "
                          f"({new_exposure:.2f} > {self.max_total_exposure:.2f})")
        
        return allowed
    
    def get_position_correlation(self) -> float:
        """
        Calculate correlation between positions to assess diversification.
        
        Returns:
            Correlation measure (0.0 to 1.0)
        """
        # This is a simplified implementation
        # A real implementation would analyze price correlation between held assets
        
        # Count unique trading pairs
        unique_pairs = set(pos['trading_pair'] for pos in self.positions.values())
        
        if len(self.positions) <= 1:
            return 0.0
        
        # Simple diversification measure: unique pairs / total positions
        diversification = len(unique_pairs) / len(self.positions)
        
        # Convert to correlation (inverse of diversification)
        correlation = 1.0 - diversification
        
        return correlation


class DrawdownMonitor:
    """Tracks and manages drawdown."""
    
    def __init__(self, config: Dict):
        """
        Initialize the drawdown monitor.
        
        Args:
            config: Risk configuration parameters
        """
        self.max_drawdown_percent = config.get('max_drawdown', 0.5)  # Default 50% max drawdown
        self.peak_capital = 0.0
        self.current_capital = 0.0
        self.drawdown_history = []  # List of (timestamp, drawdown) tuples
    
    def update_capital(self, current_capital: float) -> None:
        """
        Update current capital value.
        
        Args:
            current_capital: Current capital value
        """
        self.current_capital = current_capital
        
        # Update peak capital if current capital is higher
        if current_capital > self.peak_capital:
            self.peak_capital = current_capital
        
        # Record drawdown
        drawdown = self.calculate_drawdown()
        self.drawdown_history.append((datetime.now(), drawdown))
        
        # Keep only recent history (last 1000 points)
        if len(self.drawdown_history) > 1000:
            self.drawdown_history = self.drawdown_history[-1000:]
    
    def calculate_drawdown(self) -> float:
        """
        Calculate current drawdown as a percentage.
        
        Returns:
            Current drawdown as a percentage
        """
        if self.peak_capital == 0:
            return 0.0
        
        return (self.peak_capital - self.current_capital) / self.peak_capital
    
    def is_max_drawdown_exceeded(self) -> bool:
        """
        Check if maximum allowed drawdown is exceeded.
        
        Returns:
            True if maximum drawdown is exceeded, False otherwise
        """
        drawdown = self.calculate_drawdown()
        exceeded = drawdown > self.max_drawdown_percent
        
        if exceeded:
            logger.warning(f"Maximum drawdown exceeded: {drawdown:.2f} > {self.max_drawdown_percent:.2f}")
        
        return exceeded
    
    def get_recovery_factor(self) -> float:
        """
        Calculate recovery factor (how much gain needed to recover from drawdown).
        
        Returns:
            Recovery factor
        """
        drawdown = self.calculate_drawdown()
        
        if drawdown == 0:
            return 1.0
        
        if drawdown >= 1.0:
            return float('inf')
        
        return 1 / (1 - drawdown)
    
    def get_max_drawdown_period(self) -> Tuple[float, timedelta]:
        """
        Calculate maximum drawdown period.
        
        Returns:
            Tuple of (max drawdown, duration)
        """
        if not self.drawdown_history:
            return 0.0, timedelta(0)
        
        max_drawdown = 0.0
        max_duration = timedelta(0)
        drawdown_start = None
        
        for timestamp, drawdown in self.drawdown_history:
            if drawdown > 0 and drawdown_start is None:
                drawdown_start = timestamp
            elif drawdown == 0 and drawdown_start is not None:
                duration = timestamp - drawdown_start
                if duration > max_duration:
                    max_duration = duration
                drawdown_start = None
            
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # Check if we're still in a drawdown period
        if drawdown_start is not None:
            duration = datetime.now() - drawdown_start
            if duration > max_duration:
                max_duration = duration
        
        return max_drawdown, max_duration


class CircuitBreaker:
    """Implements circuit breakers to pause trading during adverse conditions."""
    
    def __init__(self, config: Dict):
        """
        Initialize the circuit breaker.
        
        Args:
            config: Risk configuration parameters
        """
        self.daily_loss_limit = config.get('circuit_breakers', {}).get('daily_loss_limit', 0.05)
        self.weekly_loss_limit = config.get('circuit_breakers', {}).get('weekly_loss_limit', 0.15)
        self.volatility_limit = config.get('circuit_breakers', {}).get('volatility_limit', 0.1)
        
        self.starting_capital = 0.0
        self.current_capital = 0.0
        self.daily_starting_capital = 0.0
        self.weekly_starting_capital = 0.0
        self.last_daily_reset = datetime.now()
        self.last_weekly_reset = datetime.now()
        self.circuit_broken = False
        self.circuit_break_reason = ""
        self.circuit_break_time = None
    
    def set_starting_capital(self, capital: float) -> None:
        """
        Set the starting capital.
        
        Args:
            capital: Starting capital amount
        """
        self.starting_capital = capital
        self.current_capital = capital
        self.daily_starting_capital = capital
        self.weekly_starting_capital = capital
    
    def update_capital(self, current_capital: float) -> None:
        """
        Update current capital value and check circuit breakers.
        
        Args:
            current_capital: Current capital value
        """
        self.current_capital = current_capital
        
        # Check if we need to reset daily/weekly starting capital
        now = datetime.now()
        
        # Daily reset
        if (now - self.last_daily_reset).days >= 1:
            self.daily_starting_capital = current_capital
            self.last_daily_reset = now
        
        # Weekly reset
        if (now - self.last_weekly_reset).days >= 7:
            self.weekly_starting_capital = current_capital
            self.last_weekly_reset = now
        
        # Check circuit breakers
        self._check_circuit_breakers()
    
    def _check_circuit_breakers(self) -> None:
        """Check if any circuit breakers should be triggered."""
        # Already broken
        if self.circuit_broken:
            return
        
        # Check daily loss limit
        daily_loss = (self.daily_starting_capital - self.current_capital) / self.daily_starting_capital
        if daily_loss > self.daily_loss_limit:
            self._break_circuit(f"Daily loss limit exceeded: {daily_loss:.2f} > {self.daily_loss_limit:.2f}")
            return
        
        # Check weekly loss limit
        weekly_loss = (self.weekly_starting_capital - self.current_capital) / self.weekly_starting_capital
        if weekly_loss > self.weekly_loss_limit:
            self._break_circuit(f"Weekly loss limit exceeded: {weekly_loss:.2f} > {self.weekly_loss_limit:.2f}")
            return
    
    def _break_circuit(self, reason: str) -> None:
        """
        Break the circuit and pause trading.
        
        Args:
            reason: Reason for breaking the circuit
        """
        self.circuit_broken = True
        self.circuit_break_reason = reason
        self.circuit_break_time = datetime.now()
        
        logger.warning(f"Circuit breaker triggered: {reason}")
    
    def reset_circuit(self) -> None:
        """Reset the circuit breaker."""
        if self.circuit_broken:
            logger.info(f"Circuit breaker reset. Was broken due to: {self.circuit_break_reason}")
            
            self.circuit_broken = False
            self.circuit_break_reason = ""
            self.circuit_break_time = None
    
    def is_trading_allowed(self) -> bool:
        """
        Check if trading is currently allowed.
        
        Returns:
            True if trading is allowed, False otherwise
        """
        return not self.circuit_broken


class RiskManager:
    """Coordinates all risk management components."""
    
    def __init__(self, config: Dict):
        """
        Initialize the risk manager.
        
        Args:
            config: Risk configuration parameters
        """
        self.config = config
        self.position_sizer = PositionSizer(config)
        self.stop_loss_manager = StopLossManager(config)
        self.exposure_monitor = RiskExposureMonitor(config)
        self.drawdown_monitor = DrawdownMonitor(config)
        self.circuit_breaker = CircuitBreaker(config)
        
        # Initialize with default capital
        self.available_capital = config.get('initial_capital', 10000.0)
        self.exposure_monitor.set_total_capital(self.available_capital)
        self.circuit_breaker.set_starting_capital(self.available_capital)
    
    def evaluate_signal(
        self,
        signal: Signal,
        volatility: float
    ) -> Tuple[bool, float, Optional[float]]:
        """
        Evaluate a trade signal against risk parameters.
        
        Args:
            signal: Trading signal
            volatility: Current volatility measure
            
        Returns:
            Tuple of (is_allowed, adjusted_size, stop_loss_price)
        """
        # Check if trading is allowed
        if not self.circuit_breaker.is_trading_allowed():
            logger.warning(f"Signal rejected: circuit breaker active - {self.circuit_breaker.circuit_break_reason}")
            return False, 0.0, None
        
        # Check if maximum drawdown is exceeded
        if self.drawdown_monitor.is_max_drawdown_exceeded():
            logger.warning("Signal rejected: maximum drawdown exceeded")
            return False, 0.0, None
        
        # Calculate appropriate position size
        position_size = self.position_sizer.calculate_position_size(
            strategy_id=signal.strategy_id,
            trading_pair=signal.trading_pair,
            direction=signal.direction,
            available_capital=self.available_capital,
            volatility=volatility
        )
        
        # Check if new position would exceed exposure limits
        if signal.price and not self.exposure_monitor.is_new_position_allowed(position_size, signal.price):
            logger.warning("Signal rejected: would exceed exposure limits")
            return False, 0.0, None
        
        # Calculate stop-loss level
        stop_loss = None
        if signal.price:
            stop_loss = self.stop_loss_manager.calculate_stop_loss(
                entry_price=signal.price,
                direction=signal.direction,
                volatility=volatility
            )
        
        return True, position_size, stop_loss
    
    def update_position_risk(
        self,
        position_id: str,
        current_price: float,
        current_stop: Optional[float]
    ) -> Optional[float]:
        """
        Update risk parameters for an existing position.
        
        Args:
            position_id: Position identifier
            current_price: Current market price
            current_stop: Current stop-loss level
            
        Returns:
            Updated stop-loss price level or None if no update needed
        """
        # Update position in exposure monitor
        self.exposure_monitor.update_position(position_id, current_price)
        
        # Update trailing stop if applicable
        new_stop = None
        if current_stop is not None:
            # Get position details
            position = None
            for pos_id, pos in self.exposure_monitor.positions.items():
                if pos_id == position_id:
                    position = pos
                    break
            
            if position:
                new_stop = self.stop_loss_manager.update_trailing_stop(
                    current_price=current_price,
                    direction=position['direction'],
                    current_stop=current_stop
                )
        
        return new_stop
    
    def update_account_status(self, current_capital: float) -> None:
        """
        Update account status for risk monitoring.
        
        Args:
            current_capital: Current capital value
        """
        self.available_capital = current_capital
        self.exposure_monitor.set_total_capital(current_capital)
        self.drawdown_monitor.update_capital(current_capital)
        self.circuit_breaker.update_capital(current_capital)
    
    def register_position(
        self,
        position_id: str,
        trading_pair: str,
        size: float,
        entry_price: float,
        direction: PositionSide
    ) -> None:
        """
        Register a new position with the risk manager.
        
        Args:
            position_id: Position identifier
            trading_pair: Trading pair
            size: Position size
            entry_price: Entry price
            direction: Position direction
        """
        self.exposure_monitor.add_position(
            position_id=position_id,
            trading_pair=trading_pair,
            size=size,
            entry_price=entry_price,
            direction=direction
        )
    
    def unregister_position(self, position_id: str) -> None:
        """
        Unregister a closed position from the risk manager.
        
        Args:
            position_id: Position identifier
        """
        self.exposure_monitor.remove_position(position_id)
    
    def get_risk_metrics(self) -> Dict:
        """
        Get current risk metrics.
        
        Returns:
            Dictionary of risk metrics
        """
        return {
            'total_exposure': self.exposure_monitor.calculate_total_exposure(),
            'current_drawdown': self.drawdown_monitor.calculate_drawdown(),
            'recovery_factor': self.drawdown_monitor.get_recovery_factor(),
            'position_count': len(self.exposure_monitor.positions),
            'is_max_drawdown_exceeded': self.drawdown_monitor.is_max_drawdown_exceeded(),
            'is_trading_allowed': self.circuit_breaker.is_trading_allowed(),
            'circuit_break_reason': self.circuit_breaker.circuit_break_reason,
            'position_correlation': self.exposure_monitor.get_position_correlation()
        }
    
    def reset_circuit_breaker(self) -> None:
        """Reset the circuit breaker to allow trading again."""
        self.circuit_breaker.reset_circuit()
