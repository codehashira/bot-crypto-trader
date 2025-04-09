"""
Exchange interface base class and implementations for different cryptocurrency exchanges.
This module provides a unified API for interacting with various exchanges.
"""

import abc
import hmac
import hashlib
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union

import aiohttp
import requests

from ..models.base_models import (
    Asset, Exchange, MarketData, Order, OrderSide, OrderStatus, OrderType, Trade, Wallet
)


class ExchangeInterface(abc.ABC):
    """Abstract base class for exchange interfaces."""
    
    def __init__(self, exchange: Exchange):
        """
        Initialize the exchange interface.
        
        Args:
            exchange: Exchange configuration
        """
        self.exchange = exchange
        self.session = requests.Session()
        
    @abc.abstractmethod
    async def fetch_market_data(self, trading_pair: str, interval: str = '1m', 
                               limit: int = 100) -> List[MarketData]:
        """
        Fetch historical market data for a trading pair.
        
        Args:
            trading_pair: Trading pair symbol (e.g., "BTC/USDT")
            interval: Candlestick interval (e.g., "1m", "5m", "1h", "1d")
            limit: Number of candlesticks to fetch
            
        Returns:
            List of MarketData objects
        """
        pass
    
    @abc.abstractmethod
    async def fetch_ticker(self, trading_pair: str) -> MarketData:
        """
        Fetch current ticker data for a trading pair.
        
        Args:
            trading_pair: Trading pair symbol (e.g., "BTC/USDT")
            
        Returns:
            MarketData object with current market data
        """
        pass
    
    @abc.abstractmethod
    async def fetch_order_book(self, trading_pair: str, limit: int = 20) -> Dict:
        """
        Fetch order book for a trading pair.
        
        Args:
            trading_pair: Trading pair symbol (e.g., "BTC/USDT")
            limit: Depth of the order book to fetch
            
        Returns:
            Dictionary containing bids and asks
        """
        pass
    
    @abc.abstractmethod
    async def create_order(self, trading_pair: str, order_type: OrderType, 
                          side: OrderSide, quantity: float, price: Optional[float] = None) -> Order:
        """
        Create a new order on the exchange.
        
        Args:
            trading_pair: Trading pair symbol (e.g., "BTC/USDT")
            order_type: Type of order (MARKET, LIMIT, etc.)
            side: Order side (BUY or SELL)
            quantity: Order quantity
            price: Order price (required for LIMIT orders)
            
        Returns:
            Order object with exchange-assigned ID
        """
        pass
    
    @abc.abstractmethod
    async def cancel_order(self, order_id: str, trading_pair: str) -> bool:
        """
        Cancel an existing order.
        
        Args:
            order_id: Exchange-assigned order ID
            trading_pair: Trading pair symbol (e.g., "BTC/USDT")
            
        Returns:
            True if cancellation was successful, False otherwise
        """
        pass
    
    @abc.abstractmethod
    async def fetch_order(self, order_id: str, trading_pair: str) -> Order:
        """
        Fetch details of an order.
        
        Args:
            order_id: Exchange-assigned order ID
            trading_pair: Trading pair symbol (e.g., "BTC/USDT")
            
        Returns:
            Order object with current status
        """
        pass
    
    @abc.abstractmethod
    async def fetch_open_orders(self, trading_pair: Optional[str] = None) -> List[Order]:
        """
        Fetch all open orders.
        
        Args:
            trading_pair: Optional trading pair to filter by
            
        Returns:
            List of open Order objects
        """
        pass
    
    @abc.abstractmethod
    async def fetch_balance(self) -> List[Wallet]:
        """
        Fetch account balance.
        
        Returns:
            List of Wallet objects representing balances
        """
        pass
    
    @abc.abstractmethod
    async def fetch_trades(self, trading_pair: str, limit: int = 50) -> List[Trade]:
        """
        Fetch recent trades for a trading pair.
        
        Args:
            trading_pair: Trading pair symbol (e.g., "BTC/USDT")
            limit: Number of trades to fetch
            
        Returns:
            List of Trade objects
        """
        pass


class BybitExchange(ExchangeInterface):
    """Bybit exchange implementation."""
    
    def __init__(self, exchange: Exchange):
        """Initialize Bybit exchange interface."""
        super().__init__(exchange)
        self.base_url = exchange.base_url
        self.api_key = exchange.api_key
        self.api_secret = exchange.api_secret
        
    def _generate_signature(self, params: Dict) -> Tuple[str, int]:
        """
        Generate signature for authenticated requests.
        
        Args:
            params: Request parameters
            
        Returns:
            Tuple of (signature, timestamp)
        """
        timestamp = int(time.time() * 1000)
        params['api_key'] = self.api_key
        params['timestamp'] = timestamp
        
        # Sort parameters by key
        sorted_params = sorted(params.items())
        query_string = '&'.join([f"{key}={value}" for key, value in sorted_params])
        
        # Generate signature
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature, timestamp
    
    def _format_trading_pair(self, trading_pair: str) -> str:
        """
        Format trading pair for Bybit API.
        
        Args:
            trading_pair: Trading pair in format "BTC/USDT"
            
        Returns:
            Trading pair in Bybit format "BTCUSDT"
        """
        return trading_pair.replace('/', '')
    
    async def fetch_market_data(self, trading_pair: str, interval: str = '1m', 
                               limit: int = 100) -> List[MarketData]:
        """Fetch historical market data from Bybit."""
        formatted_pair = self._format_trading_pair(trading_pair)
        
        # Map interval to Bybit format
        interval_map = {
            '1m': 1, '3m': 3, '5m': 5, '15m': 15, '30m': 30,
            '1h': 60, '2h': 120, '4h': 240, '6h': 360, '12h': 720,
            '1d': 'D', '1w': 'W', '1M': 'M'
        }
        bybit_interval = interval_map.get(interval, 1)
        
        endpoint = f"/v5/market/kline"
        params = {
            'category': 'spot',
            'symbol': formatted_pair,
            'interval': bybit_interval,
            'limit': limit
        }
        
        url = f"{self.base_url}{endpoint}"
        response = await self._make_request('GET', url, params=params)
        
        if response and 'result' in response and 'list' in response['result']:
            market_data_list = []
            for item in response['result']['list']:
                # Bybit returns data in format [timestamp, open, high, low, close, volume, ...]
                timestamp = datetime.fromtimestamp(int(item[0]) / 1000)
                market_data = MarketData(
                    exchange=self.exchange.name,
                    trading_pair=trading_pair,
                    timestamp=timestamp,
                    open_price=float(item[1]),
                    high_price=float(item[2]),
                    low_price=float(item[3]),
                    close_price=float(item[4]),
                    volume=float(item[5])
                )
                market_data_list.append(market_data)
            return market_data_list
        return []
    
    async def fetch_ticker(self, trading_pair: str) -> MarketData:
        """Fetch current ticker data from Bybit."""
        formatted_pair = self._format_trading_pair(trading_pair)
        
        endpoint = f"/v5/market/tickers"
        params = {
            'category': 'spot',
            'symbol': formatted_pair
        }
        
        url = f"{self.base_url}{endpoint}"
        response = await self._make_request('GET', url, params=params)
        
        if response and 'result' in response and 'list' in response['result'] and response['result']['list']:
            ticker = response['result']['list'][0]
            return MarketData(
                exchange=self.exchange.name,
                trading_pair=trading_pair,
                timestamp=datetime.now(),
                open_price=float(ticker.get('prevPrice24h', 0)),
                high_price=float(ticker.get('highPrice24h', 0)),
                low_price=float(ticker.get('lowPrice24h', 0)),
                close_price=float(ticker.get('lastPrice', 0)),
                volume=float(ticker.get('volume24h', 0)),
                bid_price=float(ticker.get('bid1Price', 0)),
                ask_price=float(ticker.get('ask1Price', 0)),
                bid_volume=float(ticker.get('bid1Size', 0)),
                ask_volume=float(ticker.get('ask1Size', 0))
            )
        
        # Return empty market data if API call fails
        return MarketData(
            exchange=self.exchange.name,
            trading_pair=trading_pair,
            timestamp=datetime.now(),
            open_price=0,
            high_price=0,
            low_price=0,
            close_price=0,
            volume=0
        )
    
    async def fetch_order_book(self, trading_pair: str, limit: int = 20) -> Dict:
        """Fetch order book from Bybit."""
        formatted_pair = self._format_trading_pair(trading_pair)
        
        endpoint = f"/v5/market/orderbook"
        params = {
            'category': 'spot',
            'symbol': formatted_pair,
            'limit': limit
        }
        
        url = f"{self.base_url}{endpoint}"
        response = await self._make_request('GET', url, params=params)
        
        if response and 'result' in response:
            return {
                'bids': response['result'].get('b', []),  # b for bids
                'asks': response['result'].get('a', [])   # a for asks
            }
        return {'bids': [], 'asks': []}
    
    async def create_order(self, trading_pair: str, order_type: OrderType, 
                          side: OrderSide, quantity: float, price: Optional[float] = None) -> Order:
        """Create a new order on Bybit."""
        formatted_pair = self._format_trading_pair(trading_pair)
        
        # Map order type to Bybit format
        order_type_map = {
            OrderType.MARKET: 'Market',
            OrderType.LIMIT: 'Limit',
            OrderType.STOP_LOSS: 'StopLoss',
            OrderType.TAKE_PROFIT: 'TakeProfit',
            OrderType.STOP_LIMIT: 'StopLimit'
        }
        
        # Map order side to Bybit format
        side_map = {
            OrderSide.BUY: 'Buy',
            OrderSide.SELL: 'Sell'
        }
        
        params = {
            'category': 'spot',
            'symbol': formatted_pair,
            'side': side_map[side],
            'orderType': order_type_map[order_type],
            'qty': str(quantity)
        }
        
        if order_type == OrderType.LIMIT and price is not None:
            params['price'] = str(price)
        
        signature, timestamp = self._generate_signature(params)
        params['sign'] = signature
        params['timestamp'] = timestamp
        
        endpoint = f"/v5/order/create"
        url = f"{self.base_url}{endpoint}"
        response = await self._make_request('POST', url, data=params)
        
        if response and 'result' in response:
            result = response['result']
            return Order(
                id=result.get('orderId'),
                exchange=self.exchange.name,
                trading_pair=trading_pair,
                order_type=order_type,
                side=side,
                quantity=quantity,
                price=price,
                status=OrderStatus.OPEN,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        
        # Return order with REJECTED status if API call fails
        return Order(
            exchange=self.exchange.name,
            trading_pair=trading_pair,
            order_type=order_type,
            side=side,
            quantity=quantity,
            price=price,
            status=OrderStatus.REJECTED,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    async def cancel_order(self, order_id: str, trading_pair: str) -> bool:
        """Cancel an existing order on Bybit."""
        formatted_pair = self._format_trading_pair(trading_pair)
        
        params = {
            'category': 'spot',
            'symbol': formatted_pair,
            'orderId': order_id
        }
        
        signature, timestamp = self._generate_signature(params)
        params['sign'] = signature
        params['timestamp'] = timestamp
        
        endpoint = f"/v5/order/cancel"
        url = f"{self.base_url}{endpoint}"
        response = await self._make_request('POST', url, data=params)
        
        if response and 'result' in response and 'orderId' in response['result']:
            return True
        return False
    
    async def fetch_order(self, order_id: str, trading_pair: str) -> Order:
        """Fetch details of an order from Bybit."""
        formatted_pair = self._format_trading_pair(trading_pair)
        
        params = {
            'category': 'spot',
            'symbol': formatted_pair,
            'orderId': order_id
        }
        
        signature, timestamp = self._generate_signature(params)
        params['sign'] = signature
        params['timestamp'] = timestamp
        
        endpoint = f"/v5/order/realtime"
        url = f"{self.base_url}{endpoint}"
        response = await self._make_request('GET', url, params=params)
        
        if response and 'result' in response and 'list' in response['result'] and response['result']['list']:
            order_data = response['result']['list'][0]
            
            # Map Bybit order status to our OrderStatus
            status_map = {
                'Created': OrderStatus.CREATED,
                'New': OrderStatus.OPEN,
                'PartiallyFilled': OrderStatus.PARTIALLY_FILLED,
                'Filled': OrderStatus.FILLED,
                'Cancelled': OrderStatus.CANCELED,
                'Rejected': OrderStatus.REJECTED,
                'Expired': OrderStatus.EXPIRED
            }
            
            # Map Bybit order type to our OrderType
            type_map = {
                'Market': OrderType.MARKET,
                'Limit': OrderType.LIMIT,
                'StopLoss': OrderType.STOP_LOSS,
                'TakeProfit': OrderType.TAKE_PROFIT,
                'StopLimit': OrderType.STOP_LIMIT
            }
            
            # Map Bybit order side to our OrderSide
            side_map = {
                'Buy': OrderSide.BUY,
                'Sell': OrderSide.SELL
            }
            
            return Order(
                id=order_data.get('orderId'),
                exchange=self.exchange.name,
                trading_pair=trading_pair,
                order_type=type_map.get(order_data.get('orderType'), OrderType.MARKET),
                side=side_map.get(order_data.get('side'), OrderSide.BUY),
                quantity=float(order_data.get('qty', 0)),
                price=float(order_data.get('price', 0)) if order_data.get('price') else None,
                status=status_map.get(order_data.get('orderStatus'), OrderStatus.CREATED),
                created_at=datetime.fromtimestamp(int(order_data.get('createdTime', 0)) / 1000),
                updated_at=datetime.fromtimestamp(int(order_data.get('updatedTime', 0)) / 1000),
                filled_quantity=float(order_data.get('cumExecQty', 0)),
                average_fill_price=float(order_data.get('avgPrice', 0)) if order_data.get('avgPrice') else None,
                fees=float(order_data.get('cumExecFee', 0))
            )
        
        # Return empty order if API call fails
        return Order(
            exchange=self.exchange.name,
            trading_pair=trading_pair,
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=0,
            status=OrderStatus.REJECTED
        )
    
    async def fetch_open_orders(self, trading_pair: Optional[str] = None) -> List[Order]:
        """Fetch all open orders from Bybit."""
        params = {
            'category': 'spot',
            'orderStatus': 'New,PartiallyFilled'
        }
        
        if trading_pair:
            params['symbol'] = self._format_trading_pair(trading_pair)
        
        signature, timestamp = self._generate_signature(params)
        params['sign'] = signature
        params['timestamp'] = timestamp
        
        endpoint = f"/v5/order/realtime"
        url = f"{self.base_url}{endpoint}"
        response = await self._make_request('GET', url, params=params)
        
        orders = []
        if response and 'result' in response and 'list' in response['result']:
            for order_data in response['result']['list']:
                # Map Bybit order type to our OrderType
                type_map = {
                    'Market': OrderType.MARKET,
                    'Limit': OrderType.LIMIT,
                    'StopLoss': OrderType.STOP_LOSS,
                    'TakeProfit': OrderType.TAKE_PROFIT,
                    'StopLimit': OrderType.STOP_LIMIT
                }
                
                # Map Bybit order side to our OrderSide
                side_map = {
                    'Buy': OrderSide.BUY,
                    'Sell': OrderSide.SELL
                }
                
                # Map Bybit order status to our OrderStatus
                status_map = {
                    'Created': OrderStatus.CREATED,
                    'New': OrderStatus.OPEN,
                    'PartiallyFilled': OrderStatus.PARTIALLY_FILLED
                }
                
                # Extract symbol and convert to our format (BTC/USDT)
                symbol = order_data.get('symbol', '')
                trading_pair_formatted = f"{symbol[:-4]}/{symbol[-4:]}" if len(symbol) > 4 else symbol
                
                order = Order(
                    id=order_data.get('orderId'),
                    exchange=self.exchange.name,
                    trading_pair=trading_pair_formatted,
                    order_type=type_map.get(order_data.get('orderType'), OrderType.MARKET),
                    side=side_map.get(order_data.get('side'), OrderSide.BUY),
                    quantity=float(order_data.get('qty', 0)),
                    price=float(order_data.get('price', 0)) if order_data.get('price') else None,
                    status=status_map.get(order_data.get('orderStatus'), OrderStatus.CREATED),
                    created_at=datetime.fromtimestamp(int(order_data.get('createdTime', 0)) / 1000),
                    updated_at=datetime.fromtimestamp(int(order_data.get('updatedTime', 0)) / 1000),
                    filled_quantity=float(order_data.get('cumExecQty', 0)),
                    average_fill_price=float(order_data.get('avgPrice', 0)) if order_data.get('avgPrice') else None,
                    fees=float(order_data.get('cumExecFee', 0))
                )
                orders.append(order)
        
        return orders
    
    async def fetch_balance(self) -> List[Wallet]:
        """Fetch account balance from Bybit."""
        params = {
            'accountType': 'SPOT'
        }
        
        signature, timestamp = self._generate_signature(params)
        params['sign'] = signature
        params['timestamp'] = timestamp
        
        endpoint = f"/v5/account/wallet-balance"
        url = f"{self.base_url}{endpoint}"
        response = await self._make_request('GET', url, params=params)
        
        wallets = []
        if response and 'result' in response and 'list' in response['result']:
            for account in response['result']['list']:
                if 'coin' in account:
                    for coin in account['coin']:
                        wallet = Wallet(
                            exchange=self.exchange.name,
                            asset=coin.get('coin', ''),
                            total_balance=float(coin.get('walletBalance', 0)),
                            available_balance=float(coin.get('availableToWithdraw', 0)),
                            locked_balance=float(coin.get('locked', 0)),
                            last_update_time=datetime.now()
                        )
                        wallets.append(wallet)
        
        return wallets
    
    async def fetch_trades(self, trading_pair: str, limit: int = 50) -> List[Trade]:
        """Fetch recent trades for a trading pair from Bybit."""
        formatted_pair = self._format_trading_pair(trading_pair)
        
        endpoint = f"/v5/market/trades"
        params = {
            'category': 'spot',
            'symbol': formatted_pair,
            'limit': limit
        }
        
        url = f"{self.base_url}{endpoint}"
        response = await self._make_request('GET', url, params=params)
        
        trades = []
        if response and 'result' in response and 'list' in response['result']:
            for trade_data in response['result']['list']:
                # Map Bybit side to our OrderSide
                side = OrderSide.BUY if trade_data.get('side') == 'Buy' else OrderSide.SELL
                
                trade = Trade(
                    id=trade_data.get('execId'),
                    order_id='',  # Public trades don't have order ID
                    exchange=self.exchange.name,
                    trading_pair=trading_pair,
                    side=side,
                    quantity=float(trade_data.get('size', 0)),
                    price=float(trade_data.get('price', 0)),
                    fee=0.0,  # Public trades don't have fee information
                    timestamp=datetime.fromtimestamp(int(trade_data.get('time', 0)) / 1000)
                )
                trades.append(trade)
        
        return trades
    
    async def _make_request(self, method: str, url: str, params: Optional[Dict] = None, 
                           data: Optional[Dict] = None) -> Dict:
        """
        Make HTTP request to Bybit API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            params: URL parameters for GET requests
            data: Request body for POST requests
            
        Returns:
            Response JSON as dictionary
        """
        headers = {
            'Content-Type': 'application/json',
            'X-BAPI-API-KEY': self.api_key,
            'X-BAPI-TIMESTAMP': str(int(time.time() * 1000)),
            'X-BAPI-RECV-WINDOW': '5000'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                if method == 'GET':
                    async with session.get(url, params=params, headers=headers) as response:
                        if response.status == 200:
                            return await response.json()
                        else:
                            print(f"Error in GET request: {response.status}, {await response.text()}")
                            return {}
                elif method == 'POST':
                    async with session.post(url, json=data, headers=headers) as response:
                        if response.status == 200:
                            return await response.json()
                        else:
                            print(f"Error in POST request: {response.status}, {await response.text()}")
                            return {}
        except Exception as e:
            print(f"Exception in _make_request: {e}")
            return {}


class MEXCExchange(ExchangeInterface):
    """MEXC exchange implementation."""
    
    def __init__(self, exchange: Exchange):
        """Initialize MEXC exchange interface."""
        super().__init__(exchange)
        self.base_url = exchange.base_url
        self.api_key = exchange.api_key
        self.api_secret = exchange.api_secret
    
    # Implementation of MEXC exchange methods would go here
    # Similar to BybitExchange but with MEXC-specific API endpoints and parameters
    
    async def fetch_market_data(self, trading_pair: str, interval: str = '1m', 
                               limit: int = 100) -> List[MarketData]:
        """Placeholder for MEXC implementation."""
        # Implementation would be similar to Bybit but with MEXC API specifics
        return []
    
    async def fetch_ticker(self, trading_pair: str) -> MarketData:
        """Placeholder for MEXC implementation."""
        # Implementation would be similar to Bybit but with MEXC API specifics
        return MarketData(
            exchange=self.exchange.name,
            trading_pair=trading_pair,
            timestamp=datetime.now(),
            open_price=0,
            high_price=0,
            low_price=0,
            close_price=0,
            volume=0
        )
    
    async def fetch_order_book(self, trading_pair: str, limit: int = 20) -> Dict:
        """Placeholder for MEXC implementation."""
        # Implementation would be similar to Bybit but with MEXC API specifics
        return {'bids': [], 'asks': []}
    
    async def create_order(self, trading_pair: str, order_type: OrderType, 
                          side: OrderSide, quantity: float, price: Optional[float] = None) -> Order:
        """Placeholder for MEXC implementation."""
        # Implementation would be similar to Bybit but with MEXC API specifics
        return Order(
            exchange=self.exchange.name,
            trading_pair=trading_pair,
            order_type=order_type,
            side=side,
            quantity=quantity,
            price=price,
            status=OrderStatus.CREATED
        )
    
    async def cancel_order(self, order_id: str, trading_pair: str) -> bool:
        """Placeholder for MEXC implementation."""
        # Implementation would be similar to Bybit but with MEXC API specifics
        return False
    
    async def fetch_order(self, order_id: str, trading_pair: str) -> Order:
        """Placeholder for MEXC implementation."""
        # Implementation would be similar to Bybit but with MEXC API specifics
        return Order(
            exchange=self.exchange.name,
            trading_pair=trading_pair,
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=0,
            status=OrderStatus.CREATED
        )
    
    async def fetch_open_orders(self, trading_pair: Optional[str] = None) -> List[Order]:
        """Placeholder for MEXC implementation."""
        # Implementation would be similar to Bybit but with MEXC API specifics
        return []
    
    async def fetch_balance(self) -> List[Wallet]:
        """Placeholder for MEXC implementation."""
        # Implementation would be similar to Bybit but with MEXC API specifics
        return []
    
    async def fetch_trades(self, trading_pair: str, limit: int = 50) -> List[Trade]:
        """Placeholder for MEXC implementation."""
        # Implementation would be similar to Bybit but with MEXC API specifics
        return []


class BitqueryDEXExchange(ExchangeInterface):
    """Bitquery DEX exchange implementation."""
    
    def __init__(self, exchange: Exchange):
        """Initialize Bitquery DEX exchange interface."""
        super().__init__(exchange)
        self.base_url = exchange.base_url
        self.api_key = exchange.api_key
    
    # Implementation of Bitquery DEX exchange methods would go here
    # This would be different from CEX implementations as it's focused on data retrieval
    # rather than order execution
    
    async def fetch_market_data(self, trading_pair: str, interval: str = '1m', 
                               limit: int = 100) -> List[MarketData]:
        """Placeholder for Bitquery DEX implementation."""
        # Implementation would use Bitquery's GraphQL API
        return []
    
    async def fetch_ticker(self, trading_pair: str) -> MarketData:
        """Placeholder for Bitquery DEX implementation."""
        # Implementation would use Bitquery's GraphQL API
        return MarketData(
            exchange=self.exchange.name,
            trading_pair=trading_pair,
            timestamp=datetime.now(),
            open_price=0,
            high_price=0,
            low_price=0,
            close_price=0,
            volume=0
        )
    
    async def fetch_order_book(self, trading_pair: str, limit: int = 20) -> Dict:
        """Placeholder for Bitquery DEX implementation."""
        # Implementation would use Bitquery's GraphQL API
        return {'bids': [], 'asks': []}
    
    async def create_order(self, trading_pair: str, order_type: OrderType, 
                          side: OrderSide, quantity: float, price: Optional[float] = None) -> Order:
        """Not supported for Bitquery DEX as it's read-only."""
        raise NotImplementedError("Order creation not supported for Bitquery DEX")
    
    async def cancel_order(self, order_id: str, trading_pair: str) -> bool:
        """Not supported for Bitquery DEX as it's read-only."""
        raise NotImplementedError("Order cancellation not supported for Bitquery DEX")
    
    async def fetch_order(self, order_id: str, trading_pair: str) -> Order:
        """Not supported for Bitquery DEX as it's read-only."""
        raise NotImplementedError("Order fetching not supported for Bitquery DEX")
    
    async def fetch_open_orders(self, trading_pair: Optional[str] = None) -> List[Order]:
        """Not supported for Bitquery DEX as it's read-only."""
        raise NotImplementedError("Open orders fetching not supported for Bitquery DEX")
    
    async def fetch_balance(self) -> List[Wallet]:
        """Not supported for Bitquery DEX as it's read-only."""
        raise NotImplementedError("Balance fetching not supported for Bitquery DEX")
    
    async def fetch_trades(self, trading_pair: str, limit: int = 50) -> List[Trade]:
        """Placeholder for Bitquery DEX implementation."""
        # Implementation would use Bitquery's GraphQL API
        return []


class ExchangeFactory:
    """Factory for creating exchange interfaces."""
    
    @staticmethod
    def create_exchange(exchange: Exchange) -> ExchangeInterface:
        """
        Create an exchange interface based on exchange configuration.
        
        Args:
            exchange: Exchange configuration
            
        Returns:
            ExchangeInterface implementation
        """
        if exchange.name.lower() == 'bybit':
            return BybitExchange(exchange)
        elif exchange.name.lower() == 'mexc':
            return MEXCExchange(exchange)
        elif exchange.name.lower() == 'bitquery':
            return BitqueryDEXExchange(exchange)
        else:
            raise ValueError(f"Unsupported exchange: {exchange.name}")
