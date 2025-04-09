# Cryptocurrency Trading Bot Documentation

## Overview

This cryptocurrency trading bot is designed to automate trading strategies across multiple exchanges, with a focus on trend following and arbitrage strategies. The bot includes comprehensive risk management features, performance monitoring, and supports both paper trading and live trading modes.

## Table of Contents

1. [Installation](#installation)
2. [Configuration](#configuration)
3. [Usage](#usage)
4. [Trading Strategies](#trading-strategies)
5. [Risk Management](#risk-management)
6. [Monitoring and Notifications](#monitoring-and-notifications)
7. [Backtesting and Paper Trading](#backtesting-and-paper-trading)
8. [Troubleshooting](#troubleshooting)

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Setup

1. Clone the repository or extract the provided files to your desired location.

2. Install the required dependencies:

```bash
cd crypto_trading_bot
pip install -r requirements.txt
```

The `requirements.txt` file includes all necessary packages:

```
aiohttp==3.8.5
pandas==2.0.3
numpy==1.24.3
ccxt==3.0.74
python-telegram-bot==13.15
matplotlib==3.7.2
pydantic==2.0.3
```

## Configuration

The bot is configured using a JSON configuration file. A default configuration is provided in `config.json`, which you can modify according to your needs.

### Sample Configuration

```json
{
  "mode": "paper",
  "initial_capital": 10000.0,
  "exchanges": {
    "bybit": {
      "api_key": "",
      "api_secret": "",
      "trading_pairs": ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "ADA/USDT", "DOGE/USDT"],
      "initial_balances": {"USDT": 10000.0}
    },
    "mexc": {
      "api_key": "",
      "api_secret": "",
      "trading_pairs": ["BTC/USDT", "ETH/USDT"],
      "initial_balances": {"USDT": 5000.0}
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
        "volatility_scaling": true
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
      "target_exchanges": ["bybit", "mexc"],
      "target_pairs": ["BTC/USDT", "ETH/USDT"],
      "status": "ACTIVE"
    }
  ],
  "risk_management": {
    "max_drawdown": 0.5,
    "risk_per_trade": 0.02,
    "max_exposure": 0.5,
    "circuit_breakers": {
      "daily_loss_limit": 0.05,
      "weekly_loss_limit": 0.15
    }
  },
  "monitoring": {
    "alerts": {
      "email": {
        "enabled": false,
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "username": "",
        "password": "",
        "from_address": "",
        "to_address": ""
      },
      "telegram": {
        "enabled": false,
        "bot_token": "",
        "chat_id": ""
      }
    }
  }
}
```

### Configuration Options

#### General Settings

- `mode`: Trading mode, either "paper" (simulated trading) or "live" (real trading)
- `initial_capital`: Starting capital for paper trading mode

#### Exchange Configuration

For each exchange, you need to provide:

- `api_key`: API key for the exchange (required for live trading)
- `api_secret`: API secret for the exchange (required for live trading)
- `trading_pairs`: List of trading pairs to monitor and trade
- `initial_balances`: Initial balances for paper trading mode

#### Strategy Configuration

Each strategy requires:

- `id`: Unique identifier for the strategy
- `name`: Descriptive name
- `type`: Strategy type (TREND_FOLLOWING or ARBITRAGE)
- `parameters`: Strategy-specific parameters
- `risk_parameters`: Risk management parameters for this strategy
- `target_exchanges`: Exchanges to apply this strategy to
- `target_pairs`: Trading pairs to apply this strategy to
- `status`: Strategy status (ACTIVE or INACTIVE)

#### Risk Management Configuration

- `max_drawdown`: Maximum allowed drawdown as a percentage (0.5 = 50%)
- `risk_per_trade`: Maximum risk per trade as a percentage of capital
- `max_exposure`: Maximum total exposure as a percentage of capital
- `circuit_breakers`: Conditions that will pause trading

#### Monitoring Configuration

- `alerts`: Configuration for email and Telegram notifications

## Usage

### Starting the Bot

To start the bot with the default configuration:

```bash
python -m src.main
```

To specify a different configuration file:

```bash
python -m src.main --config my_config.json
```

### Command-Line Arguments

- `--config`: Path to the configuration file (default: config.json)

### Stopping the Bot

The bot can be stopped by pressing Ctrl+C in the terminal.

## Trading Strategies

The bot currently supports two main types of trading strategies:

### Trend Following (Moving Average Crossover)

This strategy uses moving averages to identify trends:

- When the short-term moving average crosses above the long-term moving average, it generates a buy signal
- When the short-term moving average crosses below the long-term moving average, it generates a sell signal

Parameters:
- `short_window`: Period for the short-term moving average
- `long_window`: Period for the long-term moving average
- `volatility_scaling`: Whether to adjust position sizes based on market volatility

### Arbitrage

This strategy looks for price differences between exchanges:

- When the price of an asset is significantly higher on one exchange than another, it generates signals to buy on the cheaper exchange and sell on the more expensive one

Parameters:
- `min_profit_threshold`: Minimum profit percentage required to execute an arbitrage opportunity
- `max_position_size`: Maximum position size as a percentage of available capital

## Risk Management

The bot includes several risk management features to protect your capital:

### Position Sizing

- Positions are sized based on the risk_per_trade parameter and current market volatility
- Higher volatility leads to smaller position sizes to maintain consistent risk

### Stop-Loss Management

- Automatic stop-loss levels are calculated based on market volatility
- Trailing stops can be enabled to lock in profits as the market moves in your favor

### Exposure Monitoring

- The bot tracks total exposure across all positions
- New positions are rejected if they would exceed the maximum exposure limit

### Drawdown Control

- The bot monitors drawdown (decline from peak capital)
- Trading can be paused if drawdown exceeds the configured maximum

### Circuit Breakers

- Daily and weekly loss limits can be configured
- If losses exceed these limits, trading is automatically paused

## Monitoring and Notifications

### Performance Metrics

The bot tracks various performance metrics:

- Total profit/loss
- Win rate
- Maximum drawdown
- Strategy-specific performance

### Alerts

Alerts can be sent via email and/or Telegram for important events:

- Order execution
- Significant profit/loss
- Risk limit breaches
- System errors

To enable notifications:

1. For email notifications, configure the SMTP settings in the configuration file
2. For Telegram notifications, create a Telegram bot and configure the bot token and chat ID

## Backtesting and Paper Trading

### Paper Trading

Paper trading allows you to test strategies with simulated trading:

- Uses real market data
- Simulates order execution with configurable slippage and fees
- Tracks performance metrics
- No real funds are at risk

To use paper trading, set `mode` to `paper` in the configuration file.

### Backtesting

Backtesting functionality allows testing strategies against historical data:

- Load historical data for specific time periods
- Run strategies against this data
- Analyze performance metrics
- Compare different strategies and parameters

## Troubleshooting

### Common Issues

#### API Connection Problems

If you encounter issues connecting to exchanges:

1. Verify your API keys are correct and have appropriate permissions
2. Check your internet connection
3. Ensure the exchange is operational
4. Check the logs for specific error messages

#### Strategy Performance Issues

If strategies are not performing as expected:

1. Review the strategy parameters
2. Check market conditions (strategies may perform differently in different market regimes)
3. Analyze the logs to understand the decision-making process
4. Consider adjusting risk parameters

### Logging

The bot logs detailed information to help diagnose issues:

- Log files are stored in the bot's directory
- The default log level is INFO
- For more detailed logging, you can change the log level to DEBUG in the code

### Getting Help

If you encounter issues not covered in this documentation:

1. Check the logs for error messages
2. Review the configuration for any mistakes
3. Consult the source code for detailed implementation details
4. Contact the developer for assistance
