"""
Data collection module for cryptocurrency trading bot.
This module handles fetching and processing market data from various exchanges.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

from ..exchange.exchange_interface import ExchangeInterface
from ..models.base_models import MarketData, Exchange

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataCollector:
    """
    Collects and processes market data from exchanges.
    """
    
    def __init__(self, exchanges: List[ExchangeInterface]):
        """
        Initialize the data collector.
        
        Args:
            exchanges: List of exchange interfaces
        """
        self.exchanges = exchanges
        self.market_data_cache = {}  # Cache for market data
        self.order_book_cache = {}   # Cache for order books
        self.ticker_cache = {}       # Cache for tickers
    async def fetch_historical_data(self, exchange_name: str, trading_pair: str, interval: str, limit: int):
        """
        Fetch historical market data for a trading pair from an exchange.
        
        Args:
            exchange_name: Name of the exchange
            trading_pair: Trading pair symbol (e.g., 'BTC/USDT')
            interval: Time interval (e.g., '1m', '1h', '1d')
            limit: Number of data points to fetch
            
        Returns:
            List of historical market data or empty list if not available
        """
        try:
            # In a real implementation, this would call the exchange API
            # For now, we'll return simulated data
            import random
            from datetime import datetime, timedelta
            from src.models.base_models import MarketData
        
            # Generate a random price around 50,000 for BTC or 3,000 for ETH
            base_price = 50000.0 if trading_pair.startswith('BTC') else 3000.0
            
            # Generate historical data
            data = []
            for i in range(limit):
                # Create a timestamp for each data point
                timestamp = datetime.now() - timedelta(
                    minutes=i if interval == '1m' else 0,
                    hours=i if interval == '1h' else 0,
                    days=i if interval == '1d' else 0
                )
                
                # Generate a price with some random variation
                price_variation = random.uniform(-0.05, 0.05)  # ±5%
                price = base_price * (1 + price_variation)
                
                # Create a MarketData object
                market_data = MarketData(
                    exchange=exchange_name,
                    trading_pair=trading_pair,
                    timestamp=timestamp,
                    open_price=price * 0.998,
                    high_price=price * 1.005,
                    low_price=price * 0.995,
                    close_price=price,
                    volume=random.uniform(100, 1000),
                    interval=interval
                )
                
                data.append(market_data)
            
            return data
        except Exception as e:
            logger.error(f"Error fetching historical data for {trading_pair} on {exchange_name}: {e}")
            return []

    
    async def fetch_ticker(self, exchange_name: str, trading_pair: str):
        """
        Fetch current ticker data for a trading pair from an exchange.
        
        Args:
            exchange_name: Name of the exchange
            trading_pair: Trading pair symbol (e.g., 'BTC/USDT')
            
        Returns:
            Ticker data or None if not available
        """
        try:
            # In a real implementation, this would call the exchange API
            # For now, we'll return simulated data
            import random
            from datetime import datetime
            from src.models.base_models import MarketData
        
            # Generate a random price around 50,000 for BTC or 3,000 for ETH
            base_price = 50000.0 if trading_pair.startswith('BTC') else 3000.0
            price_variation = random.uniform(-0.01, 0.01)  # ±1%
            current_price = base_price * (1 + price_variation)

            # Create a MarketData object with the current price
            ticker = MarketData(
                exchange=exchange_name,
                trading_pair=trading_pair,
                timestamp=datetime.now(),
                open_price=current_price * 0.998,
                high_price=current_price * 1.002,
                low_price=current_price * 0.997,
                close_price=current_price,
                volume=random.uniform(100, 1000),
                bid_price=current_price * 0.999,
                ask_price=current_price * 1.001,
                interval="1m"
            )

            return ticker
        except Exception as e:
            logger.error(f"Error fetching ticker for {trading_pair} on {exchange_name}: {e}")
            return None
    
    async def fetch_order_book(self, exchange_name: str, trading_pair: str, 
                              limit: int = 20) -> Optional[Dict]:
        """
        Fetch order book for a trading pair.
        
        Args:
            exchange_name: Name of the exchange
            trading_pair: Trading pair symbol (e.g., "BTC/USDT")
            limit: Depth of the order book to fetch
            
        Returns:
            Dictionary containing bids and asks or None if error
        """
        exchange = self._get_exchange(exchange_name)
        if not exchange:
            logger.error(f"Exchange {exchange_name} not found")
            return None
        
        try:
            order_book = await exchange.fetch_order_book(trading_pair, limit)
            
            # Update cache
            cache_key = f"{exchange_name}:{trading_pair}:orderbook"
            self.order_book_cache[cache_key] = {
                'data': order_book,
                'timestamp': datetime.now()
            }
            
            return order_book
        except Exception as e:
            logger.error(f"Error fetching order book: {e}")
            return None
    
    async def fetch_all_tickers(self, trading_pairs: List[str]) -> Dict[str, Dict[str, MarketData]]:
        """
        Fetch tickers for multiple trading pairs across all exchanges.
        
        Args:
            trading_pairs: List of trading pair symbols
            
        Returns:
            Dictionary mapping exchange names to dictionaries mapping trading pairs to MarketData
        """
        results = {}
        tasks = []
        
        for exchange in self.exchanges:
            exchange_name = exchange.exchange.name
            results[exchange_name] = {}
            for pair in trading_pairs:
                if pair in exchange.exchange.trading_pairs:
                    task = self.fetch_ticker(exchange_name, pair)
                    tasks.append((exchange_name, pair, task))
        
        # Wait for all tasks to complete
        for exchange_name, pair, task in tasks:
            try:
                ticker = await task
                if ticker:
                    results[exchange_name][pair] = ticker
            except Exception as e:
                logger.error(f"Error in fetch_all_tickers for {exchange_name}:{pair}: {e}")
        
        return results
    
    async def fetch_arbitrage_opportunities(self, trading_pair: str, 
                                          min_profit_percent: float = 0.5) -> List[Dict]:
        """
        Fetch and analyze potential arbitrage opportunities across exchanges.
        
        Args:
            trading_pair: Trading pair to analyze
            min_profit_percent: Minimum profit percentage to consider an opportunity
            
        Returns:
            List of dictionaries containing arbitrage opportunities
        """
        # Fetch tickers from all exchanges
        tickers = {}
        for exchange in self.exchanges:
            try:
                if trading_pair in exchange.exchange.trading_pairs:
                    ticker = await exchange.fetch_ticker(trading_pair)
                    if ticker:
                        tickers[exchange.exchange.name] = ticker
            except Exception as e:
                logger.error(f"Error fetching ticker for arbitrage: {e}")
        
        # Find arbitrage opportunities
        opportunities = []
        exchange_names = list(tickers.keys())
        
        for i in range(len(exchange_names)):
            for j in range(i + 1, len(exchange_names)):
                exchange1 = exchange_names[i]
                exchange2 = exchange_names[j]
                
                ticker1 = tickers[exchange1]
                ticker2 = tickers[exchange2]
                
                # Check if we can buy on exchange1 and sell on exchange2
                if ticker1.ask_price and ticker2.bid_price:
                    profit_percent1 = (ticker2.bid_price / ticker1.ask_price - 1) * 100
                    if profit_percent1 >= min_profit_percent:
                        opportunities.append({
                            'buy_exchange': exchange1,
                            'sell_exchange': exchange2,
                            'trading_pair': trading_pair,
                            'buy_price': ticker1.ask_price,
                            'sell_price': ticker2.bid_price,
                            'profit_percent': profit_percent1
                        })
                
                # Check if we can buy on exchange2 and sell on exchange1
                if ticker2.ask_price and ticker1.bid_price:
                    profit_percent2 = (ticker1.bid_price / ticker2.ask_price - 1) * 100
                    if profit_percent2 >= min_profit_percent:
                        opportunities.append({
                            'buy_exchange': exchange2,
                            'sell_exchange': exchange1,
                            'trading_pair': trading_pair,
                            'buy_price': ticker2.ask_price,
                            'sell_price': ticker1.bid_price,
                            'profit_percent': profit_percent2
                        })
        
        return opportunities
    
    async def start_data_collection(self, trading_pairs: list, intervals: list):
        """
        Start collecting market data for specified trading pairs and intervals.
        
        Args:
            trading_pairs: List of trading pairs to collect data for
            intervals: List of time intervals to collect data for
        """
        logger.info(f"Starting data collection for {len(trading_pairs)} trading pairs")
        # In a real implementation, this would start background tasks to collect data
        # For now, we'll just log that we're starting
        return
    
    def get_cached_market_data(self, exchange_name: str, trading_pair: str, 
                              interval: str, max_age_seconds: int = 300) -> Optional[List[MarketData]]:
        """
        Get cached market data if available and not expired.
        
        Args:
            exchange_name: Name of the exchange
            trading_pair: Trading pair symbol
            interval: Candlestick interval
            max_age_seconds: Maximum age of cached data in seconds
            
        Returns:
            List of MarketData objects or None if cache miss or expired
        """
        cache_key = f"{exchange_name}:{trading_pair}:{interval}"
        cached = self.market_data_cache.get(cache_key)
        
        if cached:
            age = (datetime.now() - cached['timestamp']).total_seconds()
            if age <= max_age_seconds:
                return cached['data']
        
        return None
    
    def get_cached_ticker(self, exchange_name: str, trading_pair: str, 
                         max_age_seconds: int = 10) -> Optional[MarketData]:
        """
        Get cached ticker if available and not expired.
        
        Args:
            exchange_name: Name of the exchange
            trading_pair: Trading pair symbol
            max_age_seconds: Maximum age of cached data in seconds
            
        Returns:
            MarketData object or None if cache miss or expired
        """
        cache_key = f"{exchange_name}:{trading_pair}:ticker"
        cached = self.ticker_cache.get(cache_key)
        
        if cached:
            age = (datetime.now() - cached['timestamp']).total_seconds()
            if age <= max_age_seconds:
                return cached['data']
        
        return None
    
    def get_cached_order_book(self, exchange_name: str, trading_pair: str, 
                             max_age_seconds: int = 5) -> Optional[Dict]:
        """
        Get cached order book if available and not expired.
        
        Args:
            exchange_name: Name of the exchange
            trading_pair: Trading pair symbol
            max_age_seconds: Maximum age of cached data in seconds
            
        Returns:
            Dictionary containing bids and asks or None if cache miss or expired
        """
        cache_key = f"{exchange_name}:{trading_pair}:orderbook"
        cached = self.order_book_cache.get(cache_key)
        
        if cached:
            age = (datetime.now() - cached['timestamp']).total_seconds()
            if age <= max_age_seconds:
                return cached['data']
        
        return None
    
    def _get_exchange(self, exchange_name: str) -> Optional[ExchangeInterface]:
        """
        Get exchange interface by name.
        
        Args:
            exchange_name: Name of the exchange
            
        Returns:
            ExchangeInterface or None if not found
        """
        for exchange in self.exchanges:
            if exchange.exchange.name.lower() == exchange_name.lower():
                return exchange
        return None
