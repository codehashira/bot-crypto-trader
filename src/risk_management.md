# Risk Management System Design

This document outlines the risk management system for our cryptocurrency trading bot, designed to protect the user's capital and ensure sustainable trading.

## Core Principles

1. **Capital Preservation**: Limit maximum drawdown to 50% of trading budget as specified by user
2. **Position Sizing**: Scale position sizes based on volatility and risk metrics
3. **Diversification**: Distribute risk across multiple assets and strategies
4. **Stop-Loss Management**: Implement dynamic stop-loss mechanisms
5. **Exposure Control**: Limit total exposure across all positions

## Risk Management Components

### 1. Position Sizing Module

Determines appropriate position sizes based on:

```python
class PositionSizer:
    def calculate_position_size(
        self,
        strategy_id: str,
        trading_pair: str,
        direction: str,
        available_capital: float,
        volatility: float,
        risk_per_trade: float = 0.02  # Default 2% risk per trade
    ) -> float:
        """
        Calculate appropriate position size based on risk parameters.
        
        Args:
            strategy_id: Identifier for the strategy
            trading_pair: The trading pair (e.g., "BTC/USDT")
            direction: "LONG" or "SHORT"
            available_capital: Available capital for trading
            volatility: Current volatility measure (e.g., ATR or standard deviation)
            risk_per_trade: Maximum risk percentage per trade
            
        Returns:
            Recommended position size
        """
        # Calculate maximum capital at risk
        max_capital_at_risk = available_capital * risk_per_trade
        
        # Adjust based on volatility
        if volatility > 0:
            # Inverse relationship with volatility - higher volatility means smaller position
            position_size = max_capital_at_risk / volatility
        else:
            position_size = 0
            
        return position_size
```

### 2. Stop-Loss Manager

Manages stop-loss levels for open positions:

```python
class StopLossManager:
    def calculate_stop_loss(
        self,
        entry_price: float,
        direction: str,
        volatility: float,
        risk_multiplier: float = 2.0  # Default 2x ATR
    ) -> float:
        """
        Calculate appropriate stop-loss level based on volatility.
        
        Args:
            entry_price: Position entry price
            direction: "LONG" or "SHORT"
            volatility: Current volatility measure (e.g., ATR)
            risk_multiplier: Multiplier for volatility measure
            
        Returns:
            Stop-loss price level
        """
        if direction == "LONG":
            stop_loss = entry_price - (volatility * risk_multiplier)
        else:  # SHORT
            stop_loss = entry_price + (volatility * risk_multiplier)
            
        return stop_loss
        
    def update_trailing_stop(
        self,
        current_price: float,
        direction: str,
        current_stop: float,
        trail_percent: float = 0.05  # Default 5% trailing stop
    ) -> float:
        """
        Update trailing stop-loss level based on price movement.
        
        Args:
            current_price: Current market price
            direction: "LONG" or "SHORT"
            current_stop: Current stop-loss level
            trail_percent: Trailing percentage
            
        Returns:
            Updated stop-loss price level
        """
        if direction == "LONG":
            trail_level = current_price * (1 - trail_percent)
            return max(current_stop, trail_level)
        else:  # SHORT
            trail_level = current_price * (1 + trail_percent)
            return min(current_stop, trail_level)
```

### 3. Risk Exposure Monitor

Tracks and limits overall risk exposure:

```python
class RiskExposureMonitor:
    def __init__(self, max_total_exposure: float = 0.5):  # Default 50% max exposure
        self.positions = {}  # Dict of position_id -> position details
        self.max_total_exposure = max_total_exposure
        
    def add_position(self, position_id: str, trading_pair: str, size: float, entry_price: float, direction: str) -> None:
        """Add a new position to the monitor."""
        self.positions[position_id] = {
            'trading_pair': trading_pair,
            'size': size,
            'entry_price': entry_price,
            'direction': direction,
            'current_price': entry_price
        }
        
    def update_position(self, position_id: str, current_price: float) -> None:
        """Update a position with current market price."""
        if position_id in self.positions:
            self.positions[position_id]['current_price'] = current_price
            
    def remove_position(self, position_id: str) -> None:
        """Remove a closed position from the monitor."""
        if position_id in self.positions:
            del self.positions[position_id]
            
    def calculate_total_exposure(self) -> float:
        """Calculate total risk exposure as a percentage of capital."""
        total_exposure = sum(pos['size'] * pos['current_price'] for pos in self.positions.values())
        return total_exposure
        
    def is_new_position_allowed(self, size: float, price: float) -> bool:
        """Check if a new position would exceed maximum exposure."""
        current_exposure = self.calculate_total_exposure()
        new_exposure = current_exposure + (size * price)
        return new_exposure <= self.max_total_exposure
        
    def get_position_correlation(self) -> float:
        """Calculate correlation between positions to assess diversification."""
        # Implementation would analyze price correlation between held assets
        # Higher correlation means less diversification
        pass
```

### 4. Drawdown Monitor

Tracks and manages drawdown:

```python
class DrawdownMonitor:
    def __init__(self, max_drawdown_percent: float = 0.5):  # Default 50% max drawdown
        self.peak_capital = 0.0
        self.current_capital = 0.0
        self.max_drawdown_percent = max_drawdown_percent
        
    def update_capital(self, current_capital: float) -> None:
        """Update current capital value."""
        self.current_capital = current_capital
        self.peak_capital = max(self.peak_capital, current_capital)
        
    def calculate_drawdown(self) -> float:
        """Calculate current drawdown as a percentage."""
        if self.peak_capital == 0:
            return 0.0
        return (self.peak_capital - self.current_capital) / self.peak_capital
        
    def is_max_drawdown_exceeded(self) -> bool:
        """Check if maximum allowed drawdown is exceeded."""
        return self.calculate_drawdown() > self.max_drawdown_percent
        
    def get_recovery_factor(self) -> float:
        """Calculate recovery factor (how much gain needed to recover from drawdown)."""
        drawdown = self.calculate_drawdown()
        if drawdown == 0:
            return 1.0
        return 1 / (1 - drawdown)
```

### 5. Risk Manager

Coordinates all risk management components:

```python
class RiskManager:
    def __init__(self, config: dict):
        self.position_sizer = PositionSizer()
        self.stop_loss_manager = StopLossManager()
        self.exposure_monitor = RiskExposureMonitor(max_total_exposure=config.get('max_exposure', 0.5))
        self.drawdown_monitor = DrawdownMonitor(max_drawdown_percent=config.get('max_drawdown', 0.5))
        self.risk_per_trade = config.get('risk_per_trade', 0.02)
        
    def evaluate_trade_signal(self, signal: Signal, available_capital: float, volatility: float) -> Tuple[bool, float]:
        """
        Evaluate a trade signal against risk parameters.
        
        Returns:
            Tuple of (is_allowed, adjusted_size)
        """
        # Calculate appropriate position size
        position_size = self.position_sizer.calculate_position_size(
            strategy_id=signal.strategy_id,
            trading_pair=signal.trading_pair,
            direction=signal.direction,
            available_capital=available_capital,
            volatility=volatility,
            risk_per_trade=self.risk_per_trade
        )
        
        # Check if new position would exceed exposure limits
        is_allowed = self.exposure_monitor.is_new_position_allowed(position_size, signal.price)
        
        # Check if we're in a severe drawdown situation
        if self.drawdown_monitor.is_max_drawdown_exceeded():
            is_allowed = False
            
        return (is_allowed, position_size if is_allowed else 0.0)
        
    def calculate_stop_loss(self, entry_price: float, direction: str, volatility: float) -> float:
        """Calculate stop-loss level for a new position."""
        return self.stop_loss_manager.calculate_stop_loss(entry_price, direction, volatility)
        
    def update_position_risk(self, position_id: str, current_price: float, current_stop: float) -> float:
        """Update risk parameters for an existing position."""
        self.exposure_monitor.update_position(position_id, current_price)
        
        # Get position details
        position = self.exposure_monitor.positions.get(position_id)
        if not position:
            return current_stop
            
        # Update trailing stop if applicable
        new_stop = self.stop_loss_manager.update_trailing_stop(
            current_price=current_price,
            direction=position['direction'],
            current_stop=current_stop
        )
        
        return new_stop
        
    def update_account_status(self, current_capital: float) -> None:
        """Update account status for drawdown monitoring."""
        self.drawdown_monitor.update_capital(current_capital)
        
    def get_risk_metrics(self) -> dict:
        """Get current risk metrics."""
        return {
            'total_exposure': self.exposure_monitor.calculate_total_exposure(),
            'current_drawdown': self.drawdown_monitor.calculate_drawdown(),
            'recovery_factor': self.drawdown_monitor.get_recovery_factor(),
            'position_count': len(self.exposure_monitor.positions),
            'is_max_drawdown_exceeded': self.drawdown_monitor.is_max_drawdown_exceeded()
        }
```

## Risk Management Workflow

1. **Signal Generation**: Trading strategies generate signals
2. **Risk Evaluation**: Risk Manager evaluates signals against risk parameters
3. **Position Sizing**: Appropriate position size calculated based on volatility and risk
4. **Stop-Loss Setting**: Initial stop-loss levels determined
5. **Execution**: Orders executed if risk parameters allow
6. **Monitoring**: Continuous monitoring of positions, stops, and overall exposure
7. **Adjustment**: Dynamic adjustment of risk parameters based on market conditions

## Risk Configuration Example

```json
{
  "risk_management": {
    "max_exposure": 0.5,           // Maximum 50% of capital exposed
    "max_drawdown": 0.5,           // Maximum 50% drawdown allowed
    "risk_per_trade": 0.02,        // 2% risk per trade
    "correlation_threshold": 0.7,  // Maximum correlation between positions
    "volatility_scaling": true,    // Enable position sizing based on volatility
    "trailing_stop": {
      "enabled": true,
      "percent": 0.05              // 5% trailing stop
    },
    "circuit_breakers": {
      "daily_loss_limit": 0.05,    // Pause trading after 5% daily loss
      "weekly_loss_limit": 0.15    // Pause trading after 15% weekly loss
    }
  }
}
```

## Integration with Other Components

The Risk Management System integrates with:

1. **Strategy Engine**: Receives signals, returns risk-adjusted orders
2. **Order Execution Module**: Implements stop-loss orders
3. **Data Collection Module**: Receives volatility and correlation data
4. **Performance Analytics**: Provides drawdown and exposure metrics
5. **User Interface**: Displays risk metrics and allows configuration

This comprehensive risk management approach ensures the trading bot operates within the user's risk tolerance while maximizing potential returns.
