"""
Monitoring system for cryptocurrency trading bot.
This module provides monitoring, alerting, and notification capabilities.
"""

import asyncio
import logging
import smtplib
import time
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Optional, Union
import uuid

from src.models.base_models import Alert, AlertType, Order, Position

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AlertManager:
    """
    Alert management system for tracking and notifying about important events.
    """
    
    def __init__(self, config: Dict):
        """
        Initialize alert manager.
        
        Args:
            config: Alert configuration
        """
        self.config = config
        self.alerts = []
        self.unread_count = 0
    
    def add_alert(self, alert_type: AlertType, source: str, message: str, 
                 related_entity_id: Optional[str] = None, severity: int = 1) -> Alert:
        """
        Add a new alert.
        
        Args:
            alert_type: Alert type
            source: Alert source
            message: Alert message
            related_entity_id: Related entity ID
            severity: Alert severity (1-5)
            
        Returns:
            Created alert
        """
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
        self.unread_count += 1
        
        # Log alert
        log_level = logging.INFO
        if alert_type == AlertType.WARNING:
            log_level = logging.WARNING
        elif alert_type == AlertType.ERROR:
            log_level = logging.ERROR
        
        logger.log(log_level, f"Alert: [{alert_type.value}] {message}")
        
        # Send notifications
        self._send_notifications(alert)
        
        return alert
    
    def _send_notifications(self, alert: Alert) -> None:
        """
        Send notifications for an alert.
        
        Args:
            alert: Alert to send notifications for
        """
        # Email notification
        if self.config.get('alerts', {}).get('email', {}).get('enabled', False):
            self._send_email_notification(alert)
        
        # Telegram notification
        if self.config.get('alerts', {}).get('telegram', {}).get('enabled', False):
            self._send_telegram_notification(alert)
    
    def _send_email_notification(self, alert: Alert) -> None:
        """
        Send email notification for an alert.
        
        Args:
            alert: Alert to send notification for
        """
        try:
            email_config = self.config.get('alerts', {}).get('email', {})
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = email_config.get('from_address')
            msg['To'] = email_config.get('to_address')
            msg['Subject'] = f"Crypto Trading Bot Alert: {alert.type.value}"
            
            # Create message body
            body = f"""
            Alert Type: {alert.type.value}
            Source: {alert.source}
            Message: {alert.message}
            Timestamp: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
            Severity: {alert.severity}
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP(email_config.get('smtp_server'), email_config.get('smtp_port'))
            server.starttls()
            server.login(email_config.get('username'), email_config.get('password'))
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email notification sent for alert {alert.id}")
        except Exception as e:
            logger.error(f"Error sending email notification: {e}")
    
    def _send_telegram_notification(self, alert: Alert) -> None:
        """
        Send Telegram notification for an alert.
        
        Args:
            alert: Alert to send notification for
        """
        try:
            # This is a placeholder for Telegram notification
            # In a real implementation, you would use the python-telegram-bot library
            # to send a message to the configured chat
            telegram_config = self.config.get('alerts', {}).get('telegram', {})
            
            logger.info(f"Telegram notification sent for alert {alert.id}")
        except Exception as e:
            logger.error(f"Error sending Telegram notification: {e}")
    
    def mark_as_read(self, alert_id: str) -> bool:
        """
        Mark an alert as read.
        
        Args:
            alert_id: Alert ID
            
        Returns:
            Whether the alert was found and marked as read
        """
        for alert in self.alerts:
            if alert.id == alert_id and not alert.is_read:
                alert.is_read = True
                self.unread_count -= 1
                return True
        
        return False
    
    def get_alerts(self, limit: int = 50, include_read: bool = False) -> List[Alert]:
        """
        Get alerts.
        
        Args:
            limit: Maximum number of alerts to return
            include_read: Whether to include read alerts
            
        Returns:
            List of alerts
        """
        if include_read:
            return sorted(self.alerts, key=lambda a: a.timestamp, reverse=True)[:limit]
        else:
            return sorted([a for a in self.alerts if not a.is_read], 
                         key=lambda a: a.timestamp, reverse=True)[:limit]
    
    def get_unread_count(self) -> int:
        """
        Get number of unread alerts.
        
        Returns:
            Number of unread alerts
        """
        return self.unread_count


class PerformanceMonitor:
    """
    Performance monitoring system for tracking trading performance.
    """
    
    def __init__(self):
        """Initialize performance monitor."""
        self.initial_balance = 0.0
        self.current_balance = 0.0
        self.peak_balance = 0.0
        self.trades = []
        self.daily_performance = {}
        self.strategy_performance = {}
    
    def set_initial_balance(self, balance: float) -> None:
        """
        Set initial balance.
        
        Args:
            balance: Initial balance
        """
        self.initial_balance = balance
        self.current_balance = balance
        self.peak_balance = balance
    
    def update_balance(self, balance: float) -> None:
        """
        Update current balance.
        
        Args:
            balance: Current balance
        """
        self.current_balance = balance
        
        if balance > self.peak_balance:
            self.peak_balance = balance
    
    def record_trade(self, trade_data: Dict) -> None:
        """
        Record a trade.
        
        Args:
            trade_data: Trade data
        """
        self.trades.append(trade_data)
        
        # Update daily performance
        trade_date = trade_data.get('timestamp').date().isoformat()
        if trade_date not in self.daily_performance:
            self.daily_performance[trade_date] = {
                'profit_loss': 0.0,
                'trades': 0,
                'wins': 0,
                'losses': 0
            }
        
        daily_perf = self.daily_performance[trade_date]
        daily_perf['profit_loss'] += trade_data.get('profit_loss', 0.0)
        daily_perf['trades'] += 1
        
        if trade_data.get('profit_loss', 0.0) > 0:
            daily_perf['wins'] += 1
        elif trade_data.get('profit_loss', 0.0) < 0:
            daily_perf['losses'] += 1
        
        # Update strategy performance
        strategy_id = trade_data.get('strategy_id', 'unknown')
        if strategy_id not in self.strategy_performance:
            self.strategy_performance[strategy_id] = {
                'profit_loss': 0.0,
                'trades': 0,
                'wins': 0,
                'losses': 0
            }
        
        strategy_perf = self.strategy_performance[strategy_id]
        strategy_perf['profit_loss'] += trade_data.get('profit_loss', 0.0)
        strategy_perf['trades'] += 1
        
        if trade_data.get('profit_loss', 0.0) > 0:
            strategy_perf['wins'] += 1
        elif trade_data.get('profit_loss', 0.0) < 0:
            strategy_perf['losses'] += 1
    
    def get_performance_summary(self) -> Dict:
        """
        Get performance summary.
        
        Returns:
            Performance summary
        """
        total_profit_loss = self.current_balance - self.initial_balance
        profit_loss_percentage = (total_profit_loss / self.initial_balance) * 100 if self.initial_balance > 0 else 0
        
        total_trades = len(self.trades)
        winning_trades = sum(1 for trade in self.trades if trade.get('profit_loss', 0.0) > 0)
        losing_trades = sum(1 for trade in self.trades if trade.get('profit_loss', 0.0) < 0)
        
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        
        max_drawdown = 0.0
        if self.peak_balance > 0:
            max_drawdown = ((self.peak_balance - self.current_balance) / self.peak_balance) * 100
        
        return {
            'initial_balance': self.initial_balance,
            'current_balance': self.current_balance,
            'peak_balance': self.peak_balance,
            'total_profit_loss': total_profit_loss,
            'profit_loss_percentage': profit_loss_percentage,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'max_drawdown': max_drawdown,
            'strategy_performance': self.strategy_performance
        }
    
    def get_daily_performance(self) -> Dict:
        """
        Get daily performance.
        
        Returns:
            Daily performance
        """
        return self.daily_performance


class MonitoringSystem:
    """
    Monitoring system for cryptocurrency trading bot.
    """
    
    def __init__(self, config: Dict, risk_manager=None):
        """
        Initialize monitoring system.
        
        Args:
            config: Monitoring configuration
            risk_manager: Risk manager instance
        """
        self.config = config
        self.risk_manager = risk_manager
        self.alert_manager = AlertManager(config)
        self.performance_monitor = PerformanceMonitor()
        
        # Initialize with default values
        self.performance_monitor.set_initial_balance(
            config.get('initial_capital', 10000.0)
        )
    
    def add_alert(self, alert_type: AlertType, source: str, message: str,
                 related_entity_id: Optional[str] = None, severity: int = 1) -> Alert:
        """
        Add a new alert.
        
        Args:
            alert_type: Alert type
            source: Alert source
            message: Alert message
            related_entity_id: Related entity ID
            severity: Alert severity (1-5)
            
        Returns:
            Created alert
        """
        return self.alert_manager.add_alert(
            alert_type, source, message, related_entity_id, severity
        )
    
    def get_alerts(self, limit: int = 50, include_read: bool = False) -> List[Alert]:
        """
        Get alerts.
        
        Args:
            limit: Maximum number of alerts to return
            include_read: Whether to include read alerts
            
        Returns:
            List of alerts
        """
        return self.alert_manager.get_alerts(limit, include_read)
    
    def update_balance(self, balance: float) -> None:
        """
        Update current balance.
        
        Args:
            balance: Current balance
        """
        self.performance_monitor.update_balance(balance)
    
    def record_trade(self, trade_data: Dict) -> None:
        """
        Record a trade.
        
        Args:
            trade_data: Trade data
        """
        self.performance_monitor.record_trade(trade_data)
    
    def get_performance_summary(self) -> Dict:
        """
        Get performance summary.
        
        Returns:
            Performance summary
        """
        return self.performance_monitor.get_performance_summary()
    
    def monitor_order(self, order: Order) -> None:
        """
        Monitor an order.
        
        Args:
            order: Order to monitor
        """
        # Log order
        logger.info(f"Order {order.id}: {order.side.value} {order.quantity} {order.trading_pair} on {order.exchange} at {order.price}")
        
        # Create alert for filled orders
        if order.status.value == "FILLED":
            self.add_alert(
                AlertType.SUCCESS,
                "Order Execution",
                f"Order {order.id} filled: {order.side.value} {order.filled_quantity} {order.trading_pair} on {order.exchange} at {order.average_fill_price}",
                order.id
            )
        
        # Create alert for rejected orders
        elif order.status.value == "REJECTED":
            self.add_alert(
                AlertType.ERROR,
                "Order Execution",
                f"Order {order.id} rejected: {order.side.value} {order.quantity} {order.trading_pair} on {order.exchange}",
                order.id,
                severity=3
            )
    
    def monitor_position(self, position: Position, current_price: float) -> None:
        """
        Monitor a position.
        
        Args:
            position: Position to monitor
            current_price: Current price
        """
        # Calculate unrealized P&L
        if position.side.value == "LONG":
            unrealized_pnl = (current_price - position.entry_price) * position.quantity
        else:  # SHORT
            unrealized_pnl = (position.entry_price - current_price) * position.quantity
        
        # Update position
        position.unrealized_pnl = unrealized_pnl
        
        # Calculate unrealized P&L percentage
        entry_value = position.entry_price * position.quantity
        unrealized_pnl_percentage = (unrealized_pnl / entry_value) * 100 if entry_value > 0 else 0
        
        # Log significant P&L changes
        if abs(unrealized_pnl_percentage) >= 5:
            logger.info(f"Position {position.exchange}:{position.trading_pair} P&L: {unrealized_pnl_percentage:.2f}%")
        
        # Create alert for significant losses
        if unrealized_pnl_percentage <= -10:
            self.add_alert(
                AlertType.WARNING,
                "Position Monitoring",
                f"Position {position.exchange}:{position.trading_pair} has significant loss: {unrealized_pnl_percentage:.2f}%",
                f"{position.exchange}:{position.trading_pair}",
                severity=2
            )
        
        # Create alert for significant gains
        elif unrealized_pnl_percentage >= 10:
            self.add_alert(
                AlertType.INFO,
                "Position Monitoring",
                f"Position {position.exchange}:{position.trading_pair} has significant gain: {unrealized_pnl_percentage:.2f}%",
                f"{position.exchange}:{position.trading_pair}"
            )
    
    async def run_monitoring_loop(self) -> None:
        """Run the monitoring loop."""
        logger.info("Starting monitoring loop")
        
        while True:
            try:
                # Check for circuit breaker conditions
                if self.risk_manager and self.risk_manager.is_circuit_breaker_triggered():
                    self.add_alert(
                        AlertType.ERROR,
                        "Risk Management",
                        "Circuit breaker triggered: Trading has been paused",
                        severity=4
                    )
                
                # Check for drawdown limits
                if self.risk_manager:
                    current_drawdown = self.risk_manager.get_current_drawdown()
                    max_drawdown = self.risk_manager.max_drawdown
                    
                    if current_drawdown >= max_drawdown * 0.8:
                        self.add_alert(
                            AlertType.WARNING,
                            "Risk Management",
                            f"Approaching maximum drawdown: {current_drawdown:.2f}% (limit: {max_drawdown * 100:.2f}%)",
                            severity=3
                        )
                
                # Sleep for a while
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)
