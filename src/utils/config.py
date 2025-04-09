"""
Configuration file for the cryptocurrency trading bot.
"""

import json
import os
from typing import Dict, Any

# Default configuration
DEFAULT_CONFIG = {
    "mode": "paper",  # 'paper' or 'live'
    "initial_capital": 10000.0,
    "exchanges": {
        "bybit": {
            "api_key": "",
            "api_secret": "",
            "trading_pairs": ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "ADA/USDT", "DOGE/USDT"],
            "initial_balances": {"USDT": 10000.0}
        }
    },
    "strategies": [
        {
            "id": "ma_crossover_1",
            "name": "Moving Average Crossover",
            "type": "TREND_FOLLOWING",
            "parameters": {
                "short_window": 50,
                "long_window": 200,
                "volatility_scaling": True
            },
            "risk_parameters": {
                "risk_per_trade": 0.02,
                "max_position_size": 0.2
            },
            "target_exchanges": ["bybit"],
            "target_pairs": ["BTC/USDT", "ETH/USDT"],
            "status": "ACTIVE"
        },
        {
            "id": "arbitrage_1",
            "name": "Cross-Exchange Arbitrage",
            "type": "ARBITRAGE",
            "parameters": {
                "min_profit_threshold": 0.01,
                "max_position_size": 0.2
            },
            "risk_parameters": {
                "risk_per_trade": 0.01,
                "max_position_size": 0.1
            },
            "target_exchanges": ["bybit"],
            "target_pairs": ["BTC/USDT", "ETH/USDT"],
            "status": "ACTIVE"
        }
    ],
    "risk_management": {
        "max_drawdown": 0.5,  # 50% max drawdown
        "risk_per_trade": 0.02,  # 2% risk per trade
        "max_exposure": 0.5,  # 50% max exposure
        "circuit_breakers": {
            "daily_loss_limit": 0.05,  # 5% daily loss limit
            "weekly_loss_limit": 0.15  # 15% weekly loss limit
        }
    },
    "monitoring": {
        "alerts": {
            "email": {
                "enabled": False,
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "username": "",
                "password": "",
                "from_address": "",
                "to_address": ""
            },
            "telegram": {
                "enabled": False,
                "bot_token": "",
                "chat_id": ""
            }
        }
    }
}


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from file or create default if not exists.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Configuration dictionary
    """
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            return config
        except Exception as e:
            print(f"Error loading configuration: {e}")
            print("Using default configuration")
            return DEFAULT_CONFIG
    else:
        # Create default configuration file
        with open(config_path, 'w') as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        return DEFAULT_CONFIG


def save_config(config: Dict[str, Any], config_path: str) -> None:
    """
    Save configuration to file.
    
    Args:
        config: Configuration dictionary
        config_path: Path to configuration file
    """
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
