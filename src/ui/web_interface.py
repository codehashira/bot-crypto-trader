"""
Simple UI module for cryptocurrency trading bot.
This module provides a web-based user interface for monitoring and controlling the bot.
"""

import asyncio
import json
import logging
import os
import threading
import webbrowser
from datetime import datetime
from typing import Dict, List, Optional

import aiohttp
from aiohttp import web

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WebInterface:
    """
    Web-based user interface for the trading bot.
    """
    
    def __init__(self, host: str = '0.0.0.0', port: int = 8080):
        """
        Initialize the web interface.
        
        Args:
            host: Host to bind to
            port: Port to bind to
        """
        self.host = host
        self.port = port
        self.app = web.Application()
        self.setup_routes()
        
        # Data storage
        self.performance_data = {}
        self.alerts = []
        self.positions = []
        self.orders = []
        self.strategies = []
        
        # Reference to bot components
        self.monitoring_system = None
        self.risk_manager = None
        self.strategy_manager = None
        self.order_executor = None
        
        # Status
        self.is_running = False
    
    def setup_routes(self):
        """Set up web routes."""
        self.app.router.add_get('/', self.handle_index)
        self.app.router.add_get('/api/status', self.handle_status)
        self.app.router.add_get('/api/performance', self.handle_performance)
        self.app.router.add_get('/api/alerts', self.handle_alerts)
        self.app.router.add_get('/api/positions', self.handle_positions)
        self.app.router.add_get('/api/orders', self.handle_orders)
        self.app.router.add_get('/api/strategies', self.handle_strategies)
        self.app.router.add_post('/api/strategy/toggle', self.handle_strategy_toggle)
        self.app.router.add_post('/api/order/cancel', self.handle_order_cancel)
        self.app.router.add_post('/api/reset_circuit_breaker', self.handle_reset_circuit_breaker)
        
        # Serve static files
        self.app.router.add_static('/static/', path=os.path.join(os.path.dirname(__file__), 'static'))
    
    async def handle_index(self, request):
        """Handle index page request."""
        with open(os.path.join(os.path.dirname(__file__), 'static', 'index.html'), 'r') as f:
            content = f.read()
        return web.Response(text=content, content_type='text/html')
    
    async def handle_status(self, request):
        """Handle status API request."""
        if not self.monitoring_system or not self.risk_manager:
            return web.json_response({
                'status': 'not_initialized',
                'message': 'Bot components not initialized'
            })
        
        # Get risk metrics
        risk_metrics = self.risk_manager.get_risk_metrics() if self.risk_manager else {}
        
        # Get performance metrics
        performance_metrics = self.monitoring_system.get_performance_summary() if self.monitoring_system else {}
        
        return web.json_response({
            'status': 'running' if self.is_running else 'stopped',
            'mode': 'paper',  # TODO: Get from config
            'current_time': datetime.now().isoformat(),
            'risk_metrics': risk_metrics,
            'performance_metrics': performance_metrics
        })
    
    async def handle_performance(self, request):
        """Handle performance API request."""
        if not self.monitoring_system:
            return web.json_response({
                'status': 'error',
                'message': 'Monitoring system not initialized'
            })
        
        # Get performance metrics
        performance_metrics = self.monitoring_system.get_performance_summary()
        
        # Get daily performance
        daily_performance = self.monitoring_system.performance_monitor.get_daily_performance()
        
        return web.json_response({
            'status': 'success',
            'performance_metrics': performance_metrics,
            'daily_performance': daily_performance
        })
    
    async def handle_alerts(self, request):
        """Handle alerts API request."""
        if not self.monitoring_system:
            return web.json_response({
                'status': 'error',
                'message': 'Monitoring system not initialized'
            })
        
        # Get alerts
        include_read = request.query.get('include_read', 'false').lower() == 'true'
        limit = int(request.query.get('limit', '50'))
        
        alerts = self.monitoring_system.get_alerts(limit, include_read)
        
        # Convert to JSON-serializable format
        alerts_json = []
        for alert in alerts:
            alerts_json.append({
                'id': alert.id,
                'type': alert.type.value,
                'source': alert.source,
                'message': alert.message,
                'timestamp': alert.timestamp.isoformat(),
                'is_read': alert.is_read,
                'severity': alert.severity
            })
        
        return web.json_response({
            'status': 'success',
            'alerts': alerts_json,
            'unread_count': self.monitoring_system.alert_manager.get_unread_count()
        })
    
    async def handle_positions(self, request):
        """Handle positions API request."""
        if not self.order_executor:
            return web.json_response({
                'status': 'error',
                'message': 'Order executor not initialized'
            })
        
        # Get positions
        positions = self.order_executor.get_positions()
        
        # Convert to JSON-serializable format
        positions_json = []
        for position in positions:
            positions_json.append({
                'exchange': position.exchange,
                'trading_pair': position.trading_pair,
                'side': position.side.value,
                'entry_price': position.entry_price,
                'quantity': position.quantity,
                'unrealized_pnl': position.unrealized_pnl,
                'realized_pnl': position.realized_pnl,
                'last_update_time': position.last_update_time.isoformat() if position.last_update_time else None,
                'stop_loss_price': position.stop_loss_price
            })
        
        return web.json_response({
            'status': 'success',
            'positions': positions_json
        })
    
    async def handle_orders(self, request):
        """Handle orders API request."""
        if not self.order_executor:
            return web.json_response({
                'status': 'error',
                'message': 'Order executor not initialized'
            })
        
        # Get open orders
        open_orders = self.order_executor.get_open_orders()
        
        # Get order history
        limit = int(request.query.get('limit', '50'))
        order_history = self.order_executor.get_order_history(limit)
        
        # Convert to JSON-serializable format
        open_orders_json = []
        for order in open_orders:
            open_orders_json.append({
                'id': order.id,
                'exchange': order.exchange,
                'trading_pair': order.trading_pair,
                'order_type': order.order_type.value,
                'side': order.side.value,
                'quantity': order.quantity,
                'price': order.price,
                'status': order.status.value,
                'created_at': order.created_at.isoformat(),
                'updated_at': order.updated_at.isoformat() if order.updated_at else None
            })
        
        order_history_json = []
        for order in order_history:
            order_history_json.append({
                'id': order.id,
                'exchange': order.exchange,
                'trading_pair': order.trading_pair,
                'order_type': order.order_type.value,
                'side': order.side.value,
                'quantity': order.quantity,
                'price': order.price,
                'status': order.status.value,
                'created_at': order.created_at.isoformat(),
                'updated_at': order.updated_at.isoformat() if order.updated_at else None
            })
        
        return web.json_response({
            'status': 'success',
            'open_orders': open_orders_json,
            'order_history': order_history_json
        })
    
    async def handle_strategies(self, request):
        """Handle strategies API request."""
        if not self.strategy_manager:
            return web.json_response({
                'status': 'error',
                'message': 'Strategy manager not initialized'
            })
        
        # Get strategies
        strategies_json = []
        for strategy_id, strategy in self.strategy_manager.strategies.items():
            strategies_json.append({
                'id': strategy.id,
                'name': strategy.name,
                'type': strategy.type.value,
                'status': strategy.status,
                'target_exchanges': strategy.target_exchanges,
                'target_pairs': strategy.target_pairs,
                'parameters': strategy.parameters,
                'risk_parameters': strategy.risk_parameters
            })
        
        return web.json_response({
            'status': 'success',
            'strategies': strategies_json
        })
    
    async def handle_strategy_toggle(self, request):
        """Handle strategy toggle API request."""
        if not self.strategy_manager:
            return web.json_response({
                'status': 'error',
                'message': 'Strategy manager not initialized'
            })
        
        try:
            data = await request.json()
            strategy_id = data.get('strategy_id')
            
            if not strategy_id or strategy_id not in self.strategy_manager.strategies:
                return web.json_response({
                    'status': 'error',
                    'message': 'Invalid strategy ID'
                })
            
            strategy = self.strategy_manager.strategies[strategy_id]
            
            # Toggle strategy status
            if strategy.status == 'ACTIVE':
                strategy.status = 'INACTIVE'
            else:
                strategy.status = 'ACTIVE'
            
            return web.json_response({
                'status': 'success',
                'strategy_id': strategy_id,
                'new_status': strategy.status
            })
        except Exception as e:
            logger.error(f"Error toggling strategy: {e}")
            return web.json_response({
                'status': 'error',
                'message': str(e)
            })
    
    async def handle_order_cancel(self, request):
        """Handle order cancel API request."""
        if not self.order_executor:
            return web.json_response({
                'status': 'error',
                'message': 'Order executor not initialized'
            })
        
        try:
            data = await request.json()
            order_id = data.get('order_id')
            exchange = data.get('exchange')
            trading_pair = data.get('trading_pair')
            
            if not order_id or not exchange or not trading_pair:
                return web.json_response({
                    'status': 'error',
                    'message': 'Missing required parameters'
                })
            
            # Cancel order
            result = await self.order_executor.cancel_order(order_id, exchange, trading_pair)
            
            return web.json_response({
                'status': 'success' if result else 'error',
                'message': 'Order canceled' if result else 'Failed to cancel order'
            })
        except Exception as e:
            logger.error(f"Error canceling order: {e}")
            return web.json_response({
                'status': 'error',
                'message': str(e)
            })
    
    async def handle_reset_circuit_breaker(self, request):
        """Handle reset circuit breaker API request."""
        if not self.risk_manager:
            return web.json_response({
                'status': 'error',
                'message': 'Risk manager not initialized'
            })
        
        try:
            # Reset circuit breaker
            self.risk_manager.reset_circuit_breaker()
            
            return web.json_response({
                'status': 'success',
                'message': 'Circuit breaker reset'
            })
        except Exception as e:
            logger.error(f"Error resetting circuit breaker: {e}")
            return web.json_response({
                'status': 'error',
                'message': str(e)
            })
    
    def set_components(self, monitoring_system=None, risk_manager=None, 
                      strategy_manager=None, order_executor=None):
        """
        Set references to bot components.
        
        Args:
            monitoring_system: Monitoring system instance
            risk_manager: Risk manager instance
            strategy_manager: Strategy manager instance
            order_executor: Order executor instance
        """
        self.monitoring_system = monitoring_system
        self.risk_manager = risk_manager
        self.strategy_manager = strategy_manager
        self.order_executor = order_executor
    
    def set_running(self, is_running: bool):
        """
        Set running status.
        
        Args:
            is_running: Whether the bot is running
        """
        self.is_running = is_running
    
    async def start(self):
        """Start the web interface."""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        
        logger.info(f"Web interface started at http://{self.host}:{self.port}")
        
        # Open browser
        webbrowser.open(f"http://localhost:{self.port}")
    
    @staticmethod
    def run_in_thread(web_interface):
        """
        Run the web interface in a separate thread.
        
        Args:
            web_interface: WebInterface instance
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(web_interface.start())
        loop.run_forever()
    
    def start_in_thread(self):
        """Start the web interface in a separate thread."""
        thread = threading.Thread(target=self.run_in_thread, args=(self,))
        thread.daemon = True
        thread.start()
        return thread
