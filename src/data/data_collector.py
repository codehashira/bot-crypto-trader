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
        
    async def fetch_historical_data(self, exchange_name: str, trading_pair: str, 
                                   interval: str = '1h', limit: int = 100) -> List[MarketData]:
        """
        Fetch historical market data for a trading pair.
        
        Args:
            exchange_name: Name of the exchange
            trading_pair: Trading pair symbol (e.g., "BTC/USDT")
            interval: Candlestick interval (e.g., "1m", "5m", "1h", "1d")
            limit: Number of candlesticks to fetch
            
        Returns:
            List of MarketData objects
        """
        exchange = self._get_exchange(exchange_name)
        if not exchange:
            logger.error(f"Exchange {exchange_name} not found")
            return []
        
        try:
            market_data = await exchange.fetch_market_data(trading_pair, interval, limit)
            
            # Update cache
            cache_key = f"{exchange_name}:{trading_pair}:{interval}"
            self.market_data_cache[cache_key] = {
                'data': market_data,
                'timestamp': datetime.now()
            }
            
            return market_data
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            return []
    
    async def fetch_ticker(self, exchange_name: str, trading_pair: str) -> Optional[MarketData]:
        """
        Fetch current ticker data for a trading pair.
        
        Args:
            exchange_name: Name of the exchange
            trading_pair: Trading pair symbol (e.g., "BTC/USDT")
            
        Returns:
            MarketData object with current market data or None if error
        """
        exchange = self._get_exchange(exchange_name)
        if not exchange:
            logger.error(f"Exchange {exchange_name} not found")
            return None
        
        try:
            ticker = await exchange.fetch_ticker(trading_pair)
            
            # Update cache
            cache_key = f"{exchange_name}:{trading_pair}:ticker"
            self.ticker_cache[cache_key] = {
                'data': ticker,
                'timestamp': datetime.now()
            }
            
            return ticker
        except Exception as e:
            logger.error(f"Error fetching ticker: {e}")
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
            results[exchange.exchange.name] = {}
            for pair in trading_pairs:
                if pair in exchange.exchange.trading_pairs:
                    task = self.fetch_ticker(exchange.exchange.name, pair)
                    tasks.append((exchange.exchange.name, pair, task))
        
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
    
    async def start_data_collection(self, trading_pairs: List[str], 
                                   intervals: List[str], update_interval: int = 60):
        """
        Start continuous data collection for specified trading pairs and intervals.
        
        Args:
            trading_pairs: List of trading pair symbols
            intervals: List of candlestick intervals
            update_interval: Update frequency in seconds
        """
        while True:
            try:
                # Fetch data for all trading pairs and intervals
                for exchange in self.exchanges:
                    for pair in trading_pairs:
                        if pair in exchange.exchange.trading_pairs:
                            # Fetch ticker
                            await self.fetch_ticker(exchange.exchange.name, pair)
                            
                            # Fetch order book
                            await self.fetch_order_book(exchange.exchange.name, pair)
                            
                            # Fetch historical data for each interval
                            for interval in intervals:
                                await self.fetch_historical_data(
                                    exchange.exchange.name, pair, interval
                                )
                
                # Check for arbitrage opportunities
                for pair in trading_pairs:
                    await self.fetch_arbitrage_opportunities(pair)
                
                logger.info(f"Data collection cycle completed. Waiting {update_interval} seconds.")
                await asyncio.sleep(update_interval)
            except Exception as e:
                logger.error(f"Error in data collection cycle: {e}")
                await asyncio.sleep(10)  # Wait a bit before retrying
    
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
