"""
Monitoring and notification system for cryptocurrency trading bot.
This module handles monitoring of bot activities and sending notifications.
"""

import asyncio
import json
import logging
import smtplib
import uuid
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Optional, Set, Tuple, Union

from ..models.base_models import (
    Alert, AlertType, Order, OrderStatus, Position, Signal, Trade
)
from ..risk.risk_manager import RiskManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AlertManager:
    """Manages system alerts and notifications."""
    
    def __init__(self, config: Dict):
        """
        Initialize the alert manager.
        
        Args:
            config: Alert configuration parameters
        """
        self.config = config
        self.alerts = []  # List of alerts
        self.unread_alerts = set()  # Set of unread alert IDs
        self.email_enabled = config.get('email', {}).get('enabled', False)
        self.email_config = config.get('email', {})
        self.telegram_enabled = config.get('telegram', {}).get('enabled', False)
        self.telegram_config = config.get('telegram', {})
        self.alert_levels = config.get('alert_levels', {
            'info': True,
            'warning': True,
            'error': True,
            'success': True
        })
        
        # Initialize notification handlers
        if self.email_enabled:
            self._setup_email()
        
        if self.telegram_enabled:
            self._setup_telegram()
    
    def _setup_email(self) -> None:
        """Set up email notification handler."""
        required_fields = ['smtp_server', 'smtp_port', 'username', 'password', 'from_address', 'to_address']
        for field in required_fields:
            if field not in self.email_config:
                logger.error(f"Email configuration missing required field: {field}")
                self.email_enabled = False
                return
        
        logger.info("Email notifications enabled")
    
    def _setup_telegram(self) -> None:
        """Set up Telegram notification handler."""
        required_fields = ['bot_token', 'chat_id']
        for field in required_fields:
            if field not in self.telegram_config:
                logger.error(f"Telegram configuration missing required field: {field}")
                self.telegram_enabled = False
                return
        
        logger.info("Telegram notifications enabled")
    
    def add_alert(self, alert_type: AlertType, source: str, message: str, 
                 severity: int = 1, related_entity_id: Optional[str] = None) -> str:
        """
        Add a new alert to the system.
        
        Args:
            alert_type: Type of alert
            source: Component that generated the alert
            message: Alert message
            severity: Alert severity (1-5)
            related_entity_id: ID of related entity
            
        Returns:
            Alert ID
        """
        # Check if alert level is enabled
        if not self.alert_levels.get(alert_type.value.lower(), True):
            return ""
        
        alert_id = str(uuid.uuid4())
        alert = Alert(
            id=alert_id,
            type=alert_type,
            source=source,
            message=message,
            timestamp=datetime.now(),
            is_read=False,
            related_entity_id=related_entity_id,
            severity=severity
        )
        
        self.alerts.append(alert)
        self.unread_alerts.add(alert_id)
        
        # Send notification for high severity alerts
        if severity >= 3:
            self._send_notification(alert)
        
        logger.info(f"Alert added: {alert_type.value} - {message}")
        
        return alert_id
    
    def mark_alert_as_read(self, alert_id: str) -> None:
        """
        Mark an alert as read.
        
        Args:
            alert_id: Alert ID
        """
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.is_read = True
                if alert_id in self.unread_alerts:
                    self.unread_alerts.remove(alert_id)
                break
    
    def get_alerts(self, limit: int = 100, include_read: bool = False, 
                  min_severity: int = 1, alert_type: Optional[AlertType] = None) -> List[Alert]:
        """
        Get alerts filtered by various criteria.
        
        Args:
            limit: Maximum number of alerts to return
            include_read: Whether to include read alerts
            min_severity: Minimum severity level
            alert_type: Optional filter by alert type
            
        Returns:
            List of alerts
        """
        filtered_alerts = []
        
        for alert in reversed(self.alerts):  # Newest first
            if not include_read and alert.is_read:
                continue
            
            if alert.severity < min_severity:
                continue
            
            if alert_type and alert.type != alert_type:
                continue
            
            filtered_alerts.append(alert)
            
            if len(filtered_alerts) >= limit:
                break
        
        return filtered_alerts
    
    def get_unread_count(self) -> int:
        """
        Get count of unread alerts.
        
        Returns:
            Number of unread alerts
        """
        return len(self.unread_alerts)
    
    def _send_notification(self, alert: Alert) -> None:
        """
        Send notification for an alert.
        
        Args:
            alert: Alert to send notification for
        """
        if self.email_enabled:
            self._send_email_notification(alert)
        
        if self.telegram_enabled:
            self._send_telegram_notification(alert)
    
    def _send_email_notification(self, alert: Alert) -> None:
        """
        Send email notification.
        
        Args:
            alert: Alert to send notification for
        """
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_config['from_address']
            msg['To'] = self.email_config['to_address']
            msg['Subject'] = f"Crypto Trading Bot Alert: {alert.type.value}"
            
            body = f"""
            <html>
            <body>
                <h2>Crypto Trading Bot Alert</h2>
                <p><strong>Type:</strong> {alert.type.value}</p>
                <p><strong>Source:</strong> {alert.source}</p>
                <p><strong>Message:</strong> {alert.message}</p>
                <p><strong>Severity:</strong> {alert.severity}/5</p>
                <p><strong>Time:</strong> {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(body, 'html'))
            
            server = smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port'])
            server.starttls()
            server.login(self.email_config['username'], self.email_config['password'])
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email notification sent for alert: {alert.id}")
        except Exception as e:
            logger.error(f"Error sending email notification: {e}")
    
    def _send_telegram_notification(self, alert: Alert) -> None:
        """
        Send Telegram notification.
        
        Args:
            alert: Alert to send notification for
        """
        try:
            import requests
            
            bot_token = self.telegram_config['bot_token']
            chat_id = self.telegram_config['chat_id']
            
            message = f"""
            🚨 *Crypto Trading Bot Alert* 🚨
            
            *Type:* {alert.type.value}
            *Source:* {alert.source}
            *Message:* {alert.message}
            *Severity:* {alert.severity}/5
            *Time:* {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            
            response = requests.post(url, data=data)
            
            if response.status_code == 200:
                logger.info(f"Telegram notification sent for alert: {alert.id}")
            else:
                logger.error(f"Error sending Telegram notification: {response.text}")
        except Exception as e:
            logger.error(f"Error sending Telegram notification: {e}")


class PerformanceMonitor:
    """Monitors and tracks trading performance."""
    
    def __init__(self):
        """Initialize the performance monitor."""
        self.trades = []  # List of trades
        self.daily_pnl = {}  # Dict mapping dates to PnL
        self.strategy_performance = {}  # Dict mapping strategy IDs to performance metrics
        self.start_time = datetime.now()
        self.starting_balance = 0.0
        self.current_balance = 0.0
        self.peak_balance = 0.0
        self.lowest_balance = float('inf')
    
    def set_starting_balance(self, balance: float) -> None:
        """
        Set the starting balance.
        
        Args:
            balance: Starting balance
        """
        self.starting_balance = balance
        self.current_balance = balance
        self.peak_balance = balance
        self.lowest_balance = balance
    
    def update_balance(self, balance: float) -> None:
        """
        Update the current balance.
        
        Args:
            balance: Current balance
        """
        self.current_balance = balance
        
        if balance > self.peak_balance:
            self.peak_balance = balance
        
        if balance < self.lowest_balance:
            self.lowest_balance = balance
        
        # Update daily PnL
        today = datetime.now().date().isoformat()
        if today not in self.daily_pnl:
            self.daily_pnl[today] = 0.0
    
    def add_trade(self, trade: Trade) -> None:
        """
        Add a completed trade.
        
        Args:
            trade: Completed trade
        """
        self.trades.append(trade)
        
        # Update daily PnL
        trade_date = trade.timestamp.date().isoformat()
        if trade_date not in self.daily_pnl:
            self.daily_pnl[trade_date] = 0.0
        
        # Calculate trade PnL (simplified)
        trade_pnl = 0.0
        if trade.side.value == "SELL":
            trade_pnl = trade.price * trade.quantity
        else:  # BUY
            trade_pnl = -trade.price * trade.quantity
        
        self.daily_pnl[trade_date] += trade_pnl
        
        # Update strategy performance
        if trade.strategy_id:
            if trade.strategy_id not in self.strategy_performance:
                self.strategy_performance[trade.strategy_id] = {
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'total_pnl': 0.0,
                    'largest_win': 0.0,
                    'largest_loss': 0.0
                }
            
            perf = self.strategy_performance[trade.strategy_id]
            perf['total_trades'] += 1
            perf['total_pnl'] += trade_pnl
            
            if trade_pnl > 0:
                perf['winning_trades'] += 1
                perf['largest_win'] = max(perf['largest_win'], trade_pnl)
            elif trade_pnl < 0:
                perf['losing_trades'] += 1
                perf['largest_loss'] = min(perf['largest_loss'], trade_pnl)
    
    def get_performance_metrics(self) -> Dict:
        """
        Get overall performance metrics.
        
        Returns:
            Dictionary of performance metrics
        """
        total_trades = len(self.trades)
        winning_trades = sum(1 for trade in self.trades if self._calculate_trade_pnl(trade) > 0)
        losing_trades = sum(1 for trade in self.trades if self._calculate_trade_pnl(trade) < 0)
        
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        
        total_pnl = self.current_balance - self.starting_balance
        pnl_percent = (total_pnl / self.starting_balance) * 100 if self.starting_balance > 0 else 0.0
        
        max_drawdown = (self.peak_balance - self.lowest_balance) / self.peak_balance if self.peak_balance > 0 else 0.0
        
        return {
            'start_time': self.start_time,
            'current_time': datetime.now(),
            'starting_balance': self.starting_balance,
            'current_balance': self.current_balance,
            'total_pnl': total_pnl,
            'pnl_percent': pnl_percent,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'max_drawdown': max_drawdown,
            'peak_balance': self.peak_balance,
            'lowest_balance': self.lowest_balance
        }
    
    def get_strategy_metrics(self, strategy_id: str) -> Dict:
        """
        Get performance metrics for a specific strategy.
        
        Args:
            strategy_id: Strategy ID
            
        Returns:
            Dictionary of strategy performance metrics
        """
        if strategy_id not in self.strategy_performance:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'largest_win': 0.0,
                'largest_loss': 0.0,
                'average_win': 0.0,
                'average_loss': 0.0,
                'profit_factor': 0.0
            }
        
        perf = self.strategy_performance[strategy_id]
        
        win_rate = perf['winning_trades'] / perf['total_trades'] if perf['total_trades'] > 0 else 0.0
        
        # Calculate average win and loss
        strategy_trades = [trade for trade in self.trades if trade.strategy_id == strategy_id]
        winning_trades = [self._calculate_trade_pnl(trade) for trade in strategy_trades if self._calculate_trade_pnl(trade) > 0]
        losing_trades = [self._calculate_trade_pnl(trade) for trade in strategy_trades if self._calculate_trade_pnl(trade) < 0]
        
        average_win = sum(winning_trades) / len(winning_trades) if winning_trades else 0.0
        average_loss = sum(losing_trades) / len(losing_trades) if losing_trades else 0.0
        
        # Calculate profit factor
        gross_profit = sum(winning_trades)
        gross_loss = abs(sum(losing_trades)) if losing_trades else 0.0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        return {
            'total_trades': perf['total_trades'],
            'winning_trades': perf['winning_trades'],
            'losing_trades': perf['losing_trades'],
            'win_rate': win_rate,
            'total_pnl': perf['total_pnl'],
            'largest_win': perf['largest_win'],
            'largest_loss': perf['largest_loss'],
            'average_win': average_win,
            'average_loss': average_loss,
            'profit_factor': profit_factor
        }
    
    def get_daily_performance(self, days: int = 30) -> Dict[str, float]:
        """
        Get daily performance for the specified number of days.
        
        Args:
            days: Number of days to include
            
        Returns:
            Dictionary mapping dates to daily PnL
        """
        result = {}
        
        # Generate list of dates
        today = datetime.now().date()
        date_list = [(today - timedelta(days=i)).isoformat() for i in range(days)]
        
        # Fill in PnL values
        for date_str in date_list:
            result[date_str] = self.daily_pnl.get(date_str, 0.0)
        
        return result
    
    def _calculate_trade_pnl(self, trade: Trade) -> float:
        """
        Calculate PnL for a trade.
        
        Args:
            trade: Trade
            
        Returns:
            Trade PnL
        """
        if trade.side.value == "SELL":
            return trade.price * trade.quantity
        else:  # BUY
            return -trade.price * trade.quantity


class MonitoringSystem:
    """Coordinates monitoring and notification components."""
    
    def __init__(self, config: Dict, risk_manager: RiskManager):
        """
        Initialize the monitoring system.
        
        Args:
            config: Monitoring configuration parameters
            risk_manager: Risk manager instance
        """
        self.config = config
        self.risk_manager = risk_manager
        self.alert_manager = AlertManager(config.get('alerts', {}))
        self.performance_monitor = PerformanceMonitor()
        
        # Set initial balance
        initial_capital = config.get('initial_capital', 10000.0)
        self.performance_monitor.set_starting_balance(initial_capital)
    
    def monitor_order(self, order: Order) -> None:
        """
        Monitor an order and generate alerts if necessary.
        
        Args:
            order: Order to monitor
        """
        # Alert on order status changes
        if order.status == OrderStatus.FILLED:
            self.alert_manager.add_alert(
                alert_type=AlertType.SUCCESS,
                source="Order Execution",
                message=f"Order filled: {order.id} for {order.trading_pair} on {order.exchange}",
                severity=2
            )
        elif order.status == OrderStatus.REJECTED:
            self.alert_manager.add_alert(
                alert_type=AlertType.ERROR,
                source="Order Execution",
                message=f"Order rejected: {order.id} for {order.trading_pair} on {order.exchange}",
                severity=4,
                related_entity_id=order.id
            )
        elif order.status == OrderStatus.CANCELED:
            self.alert_manager.add_alert(
                alert_type=AlertType.INFO,
                source="Order Execution",
                message=f"Order canceled: {order.id} for {order.trading_pair} on {order.exchange}",
                severity=2
            )
    
    def monitor_position(self, position: Position, current_price: float) -> None:
        """
        Monitor a position and generate alerts if necessary.
        
        Args:
            position: Position to monitor
            current_price: Current market price
        """
        # Calculate unrealized PnL
        if position.side == PositionSide.LONG:
            unrealized_pnl = (current_price - position.entry_price) * position.quantity
            pnl_percent = (current_price / position.entry_price - 1) * 100
        else:  # SHORT
            unrealized_pnl = (position.entry_price - current_price) * position.quantity
            pnl_percent = (position.entry_price / current_price - 1) * 100
        
        # Alert on significant PnL changes
        if pnl_percent >= 10:  # 10% profit
            self.alert_manager.add_alert(
                alert_type=AlertType.SUCCESS,
                source="Position Monitor",
                message=f"Position profit: {position.trading_pair} on {position.exchange} is up {pnl_percent:.2f}%",
                severity=2
            )
        elif pnl_percent <= -10:  # 10% loss
            self.alert_manager.add_alert(
                alert_type=AlertType.WARNING,
                source="Position Monitor",
                message=f"Position loss: {position.trading_pair} on {position.exchange} is down {abs(pnl_percent):.2f}%",
                severity=3
            )
    
    def monitor_risk_metrics(self) -> None:
        """Monitor risk metrics and generate alerts if necessary."""
        risk_metrics = self.risk_manager.get_risk_metrics()
        
        # Alert on high exposure
        if risk_metrics['total_exposure'] > 0.4:  # 40% exposure
            self.alert_manager.add_alert(
                alert_type=AlertType.WARNING,
                source="Risk Monitor",
                message=f"High exposure: {risk_metrics['total_exposure'] * 100:.2f}% of capital is exposed",
                severity=3
            )
        
        # Alert on high drawdown
        if risk_metrics['current_drawdown'] > 0.2:  # 20% drawdown
            self.alert_manager.add_alert(
                alert_type=AlertType.WARNING,
                source="Risk Monitor",
                message=f"High drawdown: {risk_metrics['current_drawdown'] * 100:.2f}% from peak",
                severity=4
            )
        
        # Alert on circuit breaker
        if not risk_metrics['is_trading_allowed']:
            self.alert_manager.add_alert(
                alert_type=AlertType.ERROR,
                source="Risk Monitor",
                message=f"Circuit breaker activated: {risk_metrics['circuit_break_reason']}",
                severity=5
            )
    
    def add_trade(self, trade: Trade) -> None:
        """
        Add a completed trade to the performance monitor.
        
        Args:
            trade: Completed trade
        """
        self.performance_monitor.add_trade(trade)
        
        # Alert on trade completion
        self.alert_manager.add_alert(
            alert_type=AlertType.INFO,
            source="Trade Monitor",
            message=f"Trade completed: {trade.trading_pair} on {trade.exchange} ({trade.side.value})",
            severity=2
        )
    
    def update_balance(self, balance: float) -> None:
        """
        Update the current balance.
        
        Args:
            balance: Current balance
        """
        self.performance_monitor.update_balance(balance)
        
        # Update risk manager
        self.risk_manager.update_account_status(balance)
    
    def get_performance_summary(self) -> Dict:
        """
        Get a summary of trading performance.
        
        Returns:
            Dictionary of performance metrics
        """
        return self.performance_monitor.get_performance_metrics()
    
    def get_alerts(self, limit: int = 100, include_read: bool = False) -> List[Alert]:
        """
        Get recent alerts.
        
        Args:
            limit: Maximum number of alerts to return
            include_read: Whether to include read alerts
            
        Returns:
            List of alerts
        """
        return self.alert_manager.get_alerts(limit, include_read)
    
    async def run_monitoring_loop(self, interval: int = 60) -> None:
        """
        Run the monitoring loop.
        
        Args:
            interval: Monitoring interval in seconds
        """
        while True:
            try:
                # Monitor risk metrics
                self.monitor_risk_metrics()
                
                # Log performance metrics
                metrics = self.get_performance_summary()
                logger.info(f"Performance metrics: Balance: {metrics['current_balance']:.2f}, "
                           f"PnL: {metrics['total_pnl']:.2f} ({metrics['pnl_percent']:.2f}%), "
                           f"Win rate: {metrics['win_rate'] * 100:.2f}%, "
                           f"Drawdown: {metrics['max_drawdown'] * 100:.2f}%")
                
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(10)  # Wait a bit before retrying
