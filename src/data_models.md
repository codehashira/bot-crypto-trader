# Data Models for Cryptocurrency Trading Bot

This document outlines the key data models that will be used in our cryptocurrency trading bot.

## 1. Asset Model

Represents a cryptocurrency asset that can be traded.

```python
class Asset:
    symbol: str                # Trading symbol (e.g., "BTC")
    name: str                  # Full name (e.g., "Bitcoin")
    decimal_places: int        # Precision for price and quantity
    min_order_size: float      # Minimum order size allowed
    max_order_size: float      # Maximum order size allowed (if any)
    trading_fee: float         # Standard trading fee percentage
    is_active: bool            # Whether trading is currently enabled
```

## 2. Exchange Model

Represents a cryptocurrency exchange where trading occurs.

```python
class Exchange:
    name: str                  # Exchange name (e.g., "Bybit")
    exchange_type: str         # "CEX" or "DEX"
    base_url: str              # Base URL for API requests
    websocket_url: str         # WebSocket endpoint URL
    api_key: str               # API key (encrypted)
    api_secret: str            # API secret (encrypted)
    rate_limits: dict          # Rate limiting rules
    supported_assets: list     # List of supported assets
    trading_pairs: list        # List of available trading pairs
    is_active: bool            # Whether exchange is currently enabled
```

## 3. Market Data Model

Represents market data for a specific trading pair.

```python
class MarketData:
    exchange: str              # Exchange identifier
    trading_pair: str          # Trading pair (e.g., "BTC/USDT")
    timestamp: datetime        # Timestamp of the data point
    open_price: float          # Opening price in the period
    high_price: float          # Highest price in the period
    low_price: float           # Lowest price in the period
    close_price: float         # Closing price in the period
    volume: float              # Trading volume in the period
    num_trades: int            # Number of trades in the period
    bid_price: float           # Current highest bid price
    ask_price: float           # Current lowest ask price
    bid_volume: float          # Volume available at bid price
    ask_volume: float          # Volume available at ask price
```

## 4. Order Model

Represents a trading order.

```python
class Order:
    id: str                    # Order ID (assigned by exchange)
    exchange: str              # Exchange identifier
    trading_pair: str          # Trading pair (e.g., "BTC/USDT")
    order_type: str            # "MARKET", "LIMIT", etc.
    side: str                  # "BUY" or "SELL"
    quantity: float            # Order quantity
    price: float               # Order price (for limit orders)
    status: str                # "OPEN", "FILLED", "CANCELED", etc.
    created_at: datetime       # Order creation timestamp
    updated_at: datetime       # Last update timestamp
    filled_quantity: float     # Quantity that has been filled
    average_fill_price: float  # Average price of fills
    fees: float                # Fees paid for this order
    strategy_id: str           # ID of the strategy that created this order
```

## 5. Position Model

Represents an open position in a trading pair.

```python
class Position:
    exchange: str              # Exchange identifier
    trading_pair: str          # Trading pair (e.g., "BTC/USDT")
    side: str                  # "LONG" or "SHORT"
    entry_price: float         # Average entry price
    quantity: float            # Position size
    unrealized_pnl: float      # Current unrealized profit/loss
    realized_pnl: float        # Realized profit/loss from partial closes
    open_time: datetime        # When position was opened
    last_update_time: datetime # Last update timestamp
    stop_loss: float           # Stop loss price (if set)
    take_profit: float         # Take profit price (if set)
    strategy_id: str           # ID of the strategy managing this position
```

## 6. Strategy Model

Represents a trading strategy configuration.

```python
class Strategy:
    id: str                    # Strategy identifier
    name: str                  # Strategy name
    type: str                  # "TREND_FOLLOWING", "ARBITRAGE", etc.
    status: str                # "ACTIVE", "PAUSED", "BACKTEST"
    parameters: dict           # Strategy-specific parameters
    risk_parameters: dict      # Risk management parameters
    target_exchanges: list     # List of exchanges to trade on
    target_pairs: list         # List of trading pairs to trade
    created_at: datetime       # Creation timestamp
    updated_at: datetime       # Last update timestamp
```

## 7. Trade Model

Represents a completed trade (filled order).

```python
class Trade:
    id: str                    # Trade ID
    order_id: str              # Associated order ID
    exchange: str              # Exchange identifier
    trading_pair: str          # Trading pair (e.g., "BTC/USDT")
    side: str                  # "BUY" or "SELL"
    quantity: float            # Trade quantity
    price: float               # Trade price
    fee: float                 # Fee paid for this trade
    timestamp: datetime        # Trade execution timestamp
    strategy_id: str           # ID of the strategy that generated this trade
```

## 8. Wallet Model

Represents a wallet balance on an exchange.

```python
class Wallet:
    exchange: str              # Exchange identifier
    asset: str                 # Asset symbol (e.g., "BTC")
    total_balance: float       # Total balance
    available_balance: float   # Available balance (not in orders)
    locked_balance: float      # Balance locked in orders
    last_update_time: datetime # Last update timestamp
```

## 9. Performance Metrics Model

Represents performance metrics for a strategy.

```python
class PerformanceMetrics:
    strategy_id: str           # Strategy identifier
    start_time: datetime       # Start of evaluation period
    end_time: datetime         # End of evaluation period
    total_trades: int          # Total number of trades
    winning_trades: int        # Number of winning trades
    losing_trades: int         # Number of losing trades
    win_rate: float            # Percentage of winning trades
    profit_loss: float         # Total profit/loss
    profit_loss_percent: float # Profit/loss as percentage
    max_drawdown: float        # Maximum drawdown
    max_drawdown_percent: float # Maximum drawdown as percentage
    sharpe_ratio: float        # Sharpe ratio
    sortino_ratio: float       # Sortino ratio
    volatility: float          # Strategy volatility
```

## 10. Alert Model

Represents an alert or notification.

```python
class Alert:
    id: str                    # Alert identifier
    type: str                  # "INFO", "WARNING", "ERROR", etc.
    source: str                # Component that generated the alert
    message: str               # Alert message
    timestamp: datetime        # Alert generation timestamp
    is_read: bool              # Whether the alert has been read
    related_entity_id: str     # ID of related entity (order, position, etc.)
    severity: int              # Alert severity (1-5)
```

## Database Schema

The data models will be implemented using SQLAlchemy ORM with the following database schema:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Assets    │     │  Exchanges  │     │ Market Data │
└─────────────┘     └─────────────┘     └─────────────┘
       ▲                   ▲                   ▲
       │                   │                   │
       ▼                   ▼                   ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Orders    │────►│  Positions  │     │  Strategies │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │
       ▼                   │                   ▼
┌─────────────┐            │            ┌─────────────┐
│   Trades    │            │            │ Performance │
└─────────────┘            │            │   Metrics   │
       ▲                   │            └─────────────┘
       │                   │
       │                   ▼
┌─────────────┐     ┌─────────────┐
│   Wallets   │     │   Alerts    │
└─────────────┘     └─────────────┘
```

## Time-Series Data

For high-frequency market data, we'll use a time-series database (InfluxDB) to efficiently store and query:

1. Candlestick data (OHLCV)
2. Order book snapshots
3. Trade executions
4. Technical indicators

This approach allows for efficient storage and retrieval of time-series data while maintaining relational data in SQLite for configuration, orders, and other structured data.
