# Cryptocurrency Trading Bot - Installation Guide

This guide will walk you through the process of setting up and running the cryptocurrency trading bot.

## Prerequisites

Before you begin, ensure you have the following installed:
- Python 3.8 or higher
- pip (Python package manager)
- Git (optional, for cloning the repository)

## Installation Steps

1. **Set up the environment**

   Create a directory for the trading bot and navigate to it:
   ```bash
   mkdir -p ~/crypto_trading_bot
   cd ~/crypto_trading_bot
   ```

2. **Install required dependencies**

   Create a requirements.txt file with the following content:
   ```
   aiohttp==3.8.5
   pandas==2.0.3
   numpy==1.24.3
   ccxt==3.0.74
   python-telegram-bot==13.15
   matplotlib==3.7.2
   pydantic==2.0.3
   ```

   Then install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the bot**

   Create a configuration file named `config.json` with your specific settings:
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

   For live trading, you'll need to add your exchange API keys to the configuration.

4. **Run the bot**

   Start the bot with the default configuration:
   ```bash
   python -m src.main
   ```

   Or specify a custom configuration file:
   ```bash
   python -m src.main --config my_custom_config.json
   ```

5. **Monitor the bot**

   The bot will create log files in the current directory. You can monitor these logs to track the bot's activity:
   ```bash
   tail -f crypto_trading_bot.log
   ```

## Switching to Live Trading

When you're ready to switch from paper trading to live trading:

1. Obtain API keys from your exchange(s)
2. Update your configuration file:
   - Set `"mode": "live"`
   - Add your API keys to the exchange configuration
3. Start with small amounts until you're confident in the bot's performance

## Additional Resources

For more detailed information, refer to the main documentation in the `docs` directory.
