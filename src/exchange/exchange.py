"""
Exchange module for cryptocurrency trading bot.
This module defines the base exchange interface and types.
"""

from enum import Enum
from typing import List, Optional


class ExchangeType(Enum):
    """Types of exchanges."""
    CEX = "CEX"  # Centralized Exchange
    DEX = "DEX"  # Decentralized Exchange


class Exchange:
    """
    Base exchange class that defines the interface for all exchanges.
    """
    
    def __init__(
        self,
        name: str,
        exchange_type: ExchangeType,
        base_url: str,
        websocket_url: str,
        api_key: str = "",
        api_secret: str = "",
        trading_pairs: Optional[List[str]] = None
    ):
        """
        Initialize the exchange.
        
        Args:
            name: Exchange name
            exchange_type: Type of exchange (CEX or DEX)
            base_url: Base URL for REST API
            websocket_url: WebSocket URL for real-time data
            api_key: API key for authentication
            api_secret: API secret for authentication
            trading_pairs: List of supported trading pairs
        """
        self.name = name
        self.type = exchange_type
        self.base_url = base_url
        self.websocket_url = websocket_url
        self.api_key = api_key
        self.api_secret = api_secret
        self.trading_pairs = trading_pairs or [] 