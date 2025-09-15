"""
Web监控服务器 - 提供HTTP API和静态页面服务
"""

import json
import os
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Dict, Any

from .service import monitor
from utils.log import setup_logging

log = setup_logging()

class MonitorHTTPHandler(BaseHTTPRequestHandler):
    """HTTP请求处理器"""

    def do_GET(self):
        """处理GET请求"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        try:
            if path == "/":
                self._serve_dashboard()
            elif path == "/api/snapshot":
                self._serve_snapshot()
            elif path == "/api/signals":
                self._serve_signals()
            elif path == "/api/health":
                self._serve_health()
            elif path.startswith("/static/"):
                self._serve_static(path)
            else:
                self._serve_404()
        except Exception as e:
            log.error(f"[WEB] 处理请求错误: {e}")
            self._serve_error(500, str(e))

    def _serve_dashboard(self):
        """提供监控面板HTML页面"""
        html_content = self._get_dashboard_html()
        self._send_response(200, html_content, "text/html")

    def _serve_snapshot(self):
        """提供监控快照API"""
        snapshot = monitor.get_snapshot()
        data = self._serialize_snapshot(snapshot)
        self._send_json_response(data)

    def _serve_signals(self):
        """提供信号历史API"""
        query_params = parse_qs(urlparse(self.path).query)
        limit = int(query_params.get('limit', [50])[0])

        signals = monitor.get_recent_signals(limit)
        data = [self._serialize_signal(signal) for signal in signals]
        self._send_json_response(data)

    def _serve_health(self):
        """提供系统健康API"""
        health = monitor.get_system_health()
        data = self._serialize_health(health)
        self._send_json_response(data)

    def _serve_static(self, path: str):
        """提供静态文件（CSS/JS）"""
        file_name = os.path.basename(path)
        static_path = os.path.join(os.path.dirname(__file__), "static", file_name)

        try:
            with open(static_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if file_name.endswith('.css'):
                self._send_response(200, content, "text/css")
            elif file_name.endswith('.js'):
                self._send_response(200, content, "application/javascript")
            else:
                self._serve_404()
        except FileNotFoundError:
            log.error(f"[WEB] 静态文件未找到: {static_path}")
            self._serve_404()

    def _serve_404(self):
        """404页面"""
        self._send_response(404, "<h1>404 Not Found</h1>", "text/html")

    def _serve_error(self, code: int, message: str):
        """错误页面"""
        self._send_response(code, f"<h1>Error {code}</h1><p>{message}</p>", "text/html")

    def _send_response(self, code: int, content: str, content_type: str):
        """发送HTTP响应"""
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')  # 允许跨域
        self.end_headers()
        self.wfile.write(content.encode('utf-8'))

    def _send_json_response(self, data: Any):
        """发送JSON响应"""
        json_content = json.dumps(data, ensure_ascii=False, indent=2)
        self._send_response(200, json_content, "application/json")

    def _serialize_snapshot(self, snapshot) -> Dict[str, Any]:
        """序列化监控快照"""
        result = {
            "timestamp": snapshot.timestamp.isoformat(),
            "system_status": snapshot.system_status.value,
            "total_signals": snapshot.total_signals,
            "active_positions": snapshot.active_positions,
            "daily_pnl": round(snapshot.daily_pnl, 2),
            "data_feed_connected": snapshot.data_feed_connected,
            "trading_api_connected": snapshot.trading_api_connected,
            "cpu_usage": round(snapshot.cpu_usage, 2),
            "memory_usage": round(snapshot.memory_usage, 2),
            "uptime_seconds": snapshot.uptime_seconds,
            "symbols": {
                symbol: self._serialize_symbol_status(status)
                for symbol, status in snapshot.symbols.items()
            }
        }

        # 添加活跃股票数据
        if snapshot.most_actives:
            result["most_actives"] = self._serialize_most_actives(snapshot.most_actives)

        return result

    def _serialize_symbol_status(self, status) -> Dict[str, Any]:
        """序列化股票状态"""
        return {
            "symbol": status.symbol,
            "current_price": status.current_price,
            "price_change": status.price_change,
            "price_change_pct": status.price_change_pct,
            "trend": status.trend,
            "volatility": round(status.volatility, 4) if status.volatility else None,
            "volume_profile": status.volume_profile,
            "last_signal_type": status.last_signal_type,
            "last_signal_time": status.last_signal_time.isoformat() if status.last_signal_time else None,
            "last_signal_price": status.last_signal_price,
            "last_signal_confidence": status.last_signal_confidence,
            "position_size": status.position_size,
            "unrealized_pnl": round(status.unrealized_pnl, 2),
            "bars_received_today": status.bars_received_today,
            "last_bar_time": status.last_bar_time.isoformat() if status.last_bar_time else None
        }

    def _serialize_signal(self, signal) -> Dict[str, Any]:
        """序列化交易信号"""
        return {
            "timestamp": signal.timestamp.isoformat(),
            "symbol": signal.symbol,
            "signal_type": signal.signal_type,
            "price": signal.price,
            "confidence": signal.confidence,
            "reason": signal.reason,
            "executed": signal.executed
        }

    def _serialize_health(self, health) -> Dict[str, Any]:
        """序列化系统健康"""
        return {
            "data_stream_healthy": health.data_stream_healthy,
            "last_data_time": health.last_data_time.isoformat() if health.last_data_time else None,
            "connection_errors": health.connection_errors,
            "memory_usage_mb": round(health.memory_usage_mb, 2),
            "cpu_usage_pct": round(health.cpu_usage_pct, 2),
            "disk_usage_pct": round(health.disk_usage_pct, 2),
            "error_count_today": health.error_count_today,
            "warning_count_today": health.warning_count_today
        }

    def _serialize_most_actives(self, most_actives) -> Dict[str, Any]:
        """序列化最活跃股票"""
        return {
            "last_updated": most_actives.last_updated.isoformat(),
            "stocks": [
                {
                    "symbol": stock.symbol,
                    "volume": stock.volume,
                    "trade_count": stock.trade_count,
                    "change_percent": stock.change_percent
                }
                for stock in most_actives.stocks
            ]
        }

    def _get_dashboard_html(self) -> str:
        """获取监控面板HTML"""
        template_path = os.path.join(os.path.dirname(__file__), "templates", "dashboard.html")
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            log.error(f"[WEB] 模板文件未找到: {template_path}")
            return "<h1>监控面板加载失败</h1><p>模板文件未找到</p>"


    def log_message(self, format, *args):
        """重写日志方法，避免控制台输出过多HTTP日志"""
        pass

class WebMonitorServer:
    """Web监控服务器管理器"""

    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        self.host = host
        self.port = port
        self.server = None
        self.server_thread = None

    def start(self):
        """启动Web服务器"""
        try:
            self.server = HTTPServer((self.host, self.port), MonitorHTTPHandler)
            self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()

            log.info(f"[WEB] 监控服务器已启动: http://{self.host}:{self.port}")
            return True
        except Exception as e:
            log.error(f"[WEB] 启动监控服务器失败: {e}")
            return False

    def stop(self):
        """停止Web服务器"""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            log.info("[WEB] 监控服务器已停止")

    def get_url(self) -> str:
        """获取监控面板URL"""
        return f"http://{self.host}:{self.port}"