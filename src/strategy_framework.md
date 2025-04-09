# Strategy Implementation Framework

This document outlines the framework for implementing trading strategies in our cryptocurrency trading bot.

## Strategy Interface

All trading strategies will implement a common interface to ensure consistency and interoperability:

```python
class Strategy:
    def __init__(self, config: dict):
        """Initialize strategy with configuration parameters."""
        pass
        
    def process_market_data(self, market_data: MarketData) -> None:
        """Process new market data and update internal state."""
        pass
        
    def generate_signals(self) -> List[Signal]:
        """Generate trading signals based on current market conditions."""
        pass
        
    def on_order_update(self, order: Order) -> None:
        """Handle order status updates."""
        pass
        
    def on_trade(self, trade: Trade) -> None:
        """Handle completed trades."""
        pass
        
    def get_performance_metrics(self) -> PerformanceMetrics:
        """Return current performance metrics for this strategy."""
        pass
```

## Signal Model

Trading signals are the output of strategies and input to the order execution system:

```python
class Signal:
    strategy_id: str           # ID of the strategy generating the signal
    trading_pair: str          # Trading pair (e.g., "BTC/USDT")
    exchange: str              # Target exchange
    signal_type: str           # "ENTRY", "EXIT", "ADJUST"
    direction: str             # "LONG", "SHORT", "NEUTRAL"
    strength: float            # Signal strength (0.0 to 1.0)
    price: float               # Target price (if applicable)
    quantity: float            # Suggested quantity
    timestamp: datetime        # Signal generation time
    expiration: datetime       # Signal expiration time
    metadata: dict             # Additional strategy-specific data
```

## Trend Following Strategy Implementation

### Moving Average Crossover Strategy

```python
class MovingAverageCrossoverStrategy(Strategy):
    def __init__(self, config: dict):
        self.short_window = config.get('short_window', 50)
        self.long_window = config.get('long_window', 200)
        self.pairs = config.get('pairs', [])
        self.exchanges = config.get('exchanges', [])
        self.position_size = config.get('position_size', 0.1)  # 10% of available balance
        self.volatility_scaling = config.get('volatility_scaling', True)
        
        # Internal state
        self.short_ma = {}  # Dict to store short MA for each pair
        self.long_ma = {}   # Dict to store long MA for each pair
        self.positions = {} # Dict to track current positions
        
    def process_market_data(self, market_data: MarketData) -> None:
        pair_key = f"{market_data.exchange}:{market_data.trading_pair}"
        
        # Update moving averages
        if pair_key not in self.short_ma:
            self.short_ma[pair_key] = []
        if pair_key not in self.long_ma:
            self.long_ma[pair_key] = []
            
        self.short_ma[pair_key].append(market_data.close_price)
        self.long_ma[pair_key].append(market_data.close_price)
        
        # Keep only necessary data points
        if len(self.short_ma[pair_key]) > self.short_window:
            self.short_ma[pair_key] = self.short_ma[pair_key][-self.short_window:]
        if len(self.long_ma[pair_key]) > self.long_window:
            self.long_ma[pair_key] = self.long_ma[pair_key][-self.long_window:]
            
    def generate_signals(self) -> List[Signal]:
        signals = []
        
        for pair_key in self.short_ma:
            if len(self.short_ma[pair_key]) < self.short_window or len(self.long_ma[pair_key]) < self.long_window:
                continue
                
            exchange, trading_pair = pair_key.split(':')
            
            # Calculate current MAs
            current_short_ma = sum(self.short_ma[pair_key]) / len(self.short_ma[pair_key])
            current_long_ma = sum(self.long_ma[pair_key]) / len(self.long_ma[pair_key])
            
            # Calculate previous MAs
            prev_short_ma = sum(self.short_ma[pair_key][:-1]) / (len(self.short_ma[pair_key]) - 1)
            prev_long_ma = sum(self.long_ma[pair_key][:-1]) / (len(self.long_ma[pair_key]) - 1)
            
            # Check for crossover
            current_position = self.positions.get(pair_key, "NEUTRAL")
            
            # Bullish crossover (short MA crosses above long MA)
            if prev_short_ma <= prev_long_ma and current_short_ma > current_long_ma and current_position != "LONG":
                signal = Signal(
                    strategy_id=self.id,
                    trading_pair=trading_pair,
                    exchange=exchange,
                    signal_type="ENTRY",
                    direction="LONG",
                    strength=1.0,
                    price=self.short_ma[pair_key][-1],  # Current price
                    quantity=self.calculate_position_size(pair_key),
                    timestamp=datetime.now(),
                    expiration=datetime.now() + timedelta(hours=1),
                    metadata={"crossover_type": "bullish"}
                )
                signals.append(signal)
                
            # Bearish crossover (short MA crosses below long MA)
            elif prev_short_ma >= prev_long_ma and current_short_ma < current_long_ma and current_position != "SHORT":
                signal = Signal(
                    strategy_id=self.id,
                    trading_pair=trading_pair,
                    exchange=exchange,
                    signal_type="ENTRY",
                    direction="SHORT",
                    strength=1.0,
                    price=self.short_ma[pair_key][-1],  # Current price
                    quantity=self.calculate_position_size(pair_key),
                    timestamp=datetime.now(),
                    expiration=datetime.now() + timedelta(hours=1),
                    metadata={"crossover_type": "bearish"}
                )
                signals.append(signal)
                
        return signals
        
    def calculate_position_size(self, pair_key):
        # Basic position sizing
        base_size = self.position_size
        
        # Apply volatility scaling if enabled
        if self.volatility_scaling:
            volatility = self.calculate_volatility(pair_key)
            target_volatility = 0.02  # 2% daily volatility target
            volatility_scalar = target_volatility / volatility if volatility > 0 else 1.0
            return base_size * volatility_scalar
        
        return base_size
        
    def calculate_volatility(self, pair_key):
        # Calculate daily volatility using standard deviation of returns
        prices = self.short_ma[pair_key]
        if len(prices) < 2:
            return 0.0
            
        returns = [(prices[i] / prices[i-1]) - 1 for i in range(1, len(prices))]
        return statistics.stdev(returns) if returns else 0.0
```

## Arbitrage Strategy Implementation

### Cross-Exchange Arbitrage Strategy

```python
class CrossExchangeArbitrageStrategy(Strategy):
    def __init__(self, config: dict):
        self.pairs = config.get('pairs', [])
        self.exchanges = config.get('exchanges', [])
        self.min_profit_threshold = config.get('min_profit_threshold', 0.01)  # 1% minimum profit
        self.max_position_size = config.get('max_position_size', 0.2)  # 20% of available balance
        self.execution_delay = config.get('execution_delay', 5)  # seconds
        
        # Internal state
        self.market_prices = {}  # Dict to store current prices across exchanges
        self.fee_rates = {}      # Dict to store fee rates for exchanges
        self.transfer_times = {} # Dict to store estimated transfer times between exchanges
        
    def process_market_data(self, market_data: MarketData) -> None:
        key = f"{market_data.exchange}:{market_data.trading_pair}"
        self.market_prices[key] = {
            'bid': market_data.bid_price,
            'ask': market_data.ask_price,
            'timestamp': market_data.timestamp
        }
        
    def generate_signals(self) -> List[Signal]:
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
                if price_data['bid'] > best_bid['price']:
                    best_bid = {'exchange': exchange, 'price': price_data['bid']}
                if price_data['ask'] < best_ask['price']:
                    best_ask = {'exchange': exchange, 'price': price_data['ask']}
                    
            # Calculate potential profit
            if best_bid['exchange'] != best_ask['exchange']:
                spread = best_bid['price'] - best_ask['price']
                spread_percentage = spread / best_ask['price']
                
                # Account for fees
                buy_fee = self.fee_rates.get(best_ask['exchange'], 0.001)  # Default 0.1%
                sell_fee = self.fee_rates.get(best_bid['exchange'], 0.001)  # Default 0.1%
                total_fee_percentage = buy_fee + sell_fee
                
                net_profit_percentage = spread_percentage - total_fee_percentage
                
                # Check if profitable after fees and transfer time
                if net_profit_percentage > self.min_profit_threshold:
                    # Generate buy signal
                    buy_signal = Signal(
                        strategy_id=self.id,
                        trading_pair=pair,
                        exchange=best_ask['exchange'],
                        signal_type="ENTRY",
                        direction="LONG",
                        strength=min(1.0, net_profit_percentage * 10),  # Scale strength by profit
                        price=best_ask['price'],
                        quantity=self.calculate_position_size(pair, net_profit_percentage),
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
                        signal_type="EXIT",
                        direction="LONG",
                        strength=min(1.0, net_profit_percentage * 10),  # Scale strength by profit
                        price=best_bid['price'],
                        quantity=self.calculate_position_size(pair, net_profit_percentage),
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
                    
        return signals
        
    def calculate_position_size(self, pair, profit_percentage):
        # Scale position size based on profit potential
        base_size = self.max_position_size * min(1.0, profit_percentage * 10)
        
        # Additional position sizing logic can be added here
        return base_size
```

## Strategy Factory

To facilitate the creation and management of strategies:

```python
class StrategyFactory:
    @staticmethod
    def create_strategy(strategy_type: str, config: dict) -> Strategy:
        """Create a strategy instance based on type and configuration."""
        if strategy_type == "MOVING_AVERAGE_CROSSOVER":
            return MovingAverageCrossoverStrategy(config)
        elif strategy_type == "CROSS_EXCHANGE_ARBITRAGE":
            return CrossExchangeArbitrageStrategy(config)
        # Add more strategy types as needed
        else:
            raise ValueError(f"Unknown strategy type: {strategy_type}")
```

## Strategy Manager

To coordinate multiple strategies:

```python
class StrategyManager:
    def __init__(self):
        self.strategies = {}  # Dict of strategy_id -> Strategy
        
    def add_strategy(self, strategy_id: str, strategy_type: str, config: dict) -> None:
        """Add a new strategy to the manager."""
        strategy = StrategyFactory.create_strategy(strategy_type, config)
        self.strategies[strategy_id] = strategy
        
    def remove_strategy(self, strategy_id: str) -> None:
        """Remove a strategy from the manager."""
        if strategy_id in self.strategies:
            del self.strategies[strategy_id]
            
    def process_market_data(self, market_data: MarketData) -> None:
        """Process market data through all active strategies."""
        for strategy in self.strategies.values():
            strategy.process_market_data(market_data)
            
    def generate_signals(self) -> List[Signal]:
        """Generate signals from all active strategies."""
        all_signals = []
        for strategy in self.strategies.values():
            signals = strategy.generate_signals()
            all_signals.extend(signals)
        return all_signals
        
    def on_order_update(self, order: Order) -> None:
        """Propagate order updates to the relevant strategy."""
        if order.strategy_id in self.strategies:
            self.strategies[order.strategy_id].on_order_update(order)
            
    def on_trade(self, trade: Trade) -> None:
        """Propagate trade notifications to the relevant strategy."""
        if trade.strategy_id in self.strategies:
            self.strategies[trade.strategy_id].on_trade(trade)
            
    def get_performance_metrics(self) -> Dict[str, PerformanceMetrics]:
        """Get performance metrics for all strategies."""
        metrics = {}
        for strategy_id, strategy in self.strategies.items():
            metrics[strategy_id] = strategy.get_performance_metrics()
        return metrics
```

## Strategy Configuration Examples

### Moving Average Crossover Strategy Configuration

```json
{
  "strategy_id": "ma_crossover_btc_usdt",
  "strategy_type": "MOVING_AVERAGE_CROSSOVER",
  "config": {
    "short_window": 50,
    "long_window": 200,
    "pairs": ["BTC/USDT", "ETH/USDT"],
    "exchanges": ["bybit"],
    "position_size": 0.1,
    "volatility_scaling": true
  }
}
```

### Cross-Exchange Arbitrage Strategy Configuration

```json
{
  "strategy_id": "arb_btc_usdt",
  "strategy_type": "CROSS_EXCHANGE_ARBITRAGE",
  "config": {
    "pairs": ["BTC/USDT", "ETH/USDT"],
    "exchanges": ["bybit", "mexc"],
    "min_profit_threshold": 0.005,
    "max_position_size": 0.15,
    "execution_
(Content truncated due to size limit. Use line ranges to read in chunks)