class MonitorDashboard {
    constructor() {
        this.updateInterval = 2000; // 2秒更新一次
        this.isUpdating = false;
        this.init();
    }

    init() {
        this.updateData();
        setInterval(() => this.updateData(), this.updateInterval);
    }

    async updateData() {
        if (this.isUpdating) return;
        this.isUpdating = true;

        try {
            await Promise.all([
                this.updateSnapshot(),
                this.updateSignals()
            ]);
        } catch (error) {
            console.error('更新数据失败:', error);
        } finally {
            this.isUpdating = false;
        }
    }

    async updateSnapshot() {
        try {
            const response = await fetch('/api/snapshot');
            const data = await response.json();
            this.renderSnapshot(data);
        } catch (error) {
            console.error('获取监控快照失败:', error);
        }
    }

    async updateSignals() {
        try {
            const response = await fetch('/api/signals?limit=10');
            const data = await response.json();
            this.renderSignals(data);
        } catch (error) {
            console.error('获取信号历史失败:', error);
        }
    }

    renderSnapshot(data) {
        // 更新系统状态
        const statusEl = document.getElementById('system-status');
        statusEl.textContent = data.system_status;
        statusEl.className = 'status-indicator ' +
            data.system_status.toLowerCase().replace(/[^a-z]/g, '');

        // 更新最后更新时间
        document.getElementById('last-update').textContent =
            '最后更新: ' + new Date(data.timestamp).toLocaleTimeString();

        // 更新概览指标
        document.getElementById('total-signals').textContent = data.total_signals;
        document.getElementById('active-positions').textContent = data.active_positions;

        const pnlEl = document.getElementById('daily-pnl');
        pnlEl.textContent = '$' + data.daily_pnl.toFixed(2);
        pnlEl.style.color = data.daily_pnl >= 0 ? '#27ae60' : '#e74c3c';

        // 更新连接状态
        const dataFeedEl = document.getElementById('data-feed-status');
        dataFeedEl.className = 'connection-indicator ' +
            (data.data_feed_connected ? 'connected' : 'disconnected');

        const tradingApiEl = document.getElementById('trading-api-status');
        tradingApiEl.className = 'connection-indicator ' +
            (data.trading_api_connected ? 'connected' : 'disconnected');

        // 更新系统性能
        document.getElementById('cpu-usage').textContent = data.cpu_usage + '%';
        document.getElementById('memory-usage').textContent = data.memory_usage + '%';
        document.getElementById('uptime').textContent = this.formatUptime(data.uptime_seconds);

        // 更新股票状态
        this.renderSymbols(data.symbols);
    }

    renderSymbols(symbols) {
        const container = document.getElementById('symbols-list');

        if (Object.keys(symbols).length === 0) {
            container.innerHTML = '<p>暂无股票数据</p>';
            return;
        }

        const html = Object.values(symbols).map(symbol => `
            <div class="symbol-item">
                <div>
                    <span class="symbol-name">${symbol.symbol}</span>
                    <span class="symbol-trend trend-${symbol.trend.toLowerCase()}">
                        ${symbol.trend}
                    </span>
                </div>
                <div>
                    <span class="symbol-price">
                        $${symbol.current_price ? symbol.current_price.toFixed(2) : '--'}
                    </span>
                    ${symbol.price_change_pct ?
                        `<span style="color: ${symbol.price_change_pct >= 0 ? '#27ae60' : '#e74c3c'}">
                            ${symbol.price_change_pct.toFixed(2)}%
                        </span>` : ''
                    }
                </div>
            </div>
        `).join('');

        container.innerHTML = html;
    }

    renderSignals(signals) {
        const container = document.getElementById('signals-list');

        if (signals.length === 0) {
            container.innerHTML = '<p>暂无信号数据</p>';
            return;
        }

        const html = signals.slice(0, 10).map(signal => `
            <div class="signal-item">
                <div class="signal-header">
                    <span class="signal-type signal-${signal.signal_type.toLowerCase()}">
                        ${signal.signal_type}
                    </span>
                    <span>${signal.symbol}</span>
                    <span>$${signal.price.toFixed(2)}</span>
                    <span>${new Date(signal.timestamp).toLocaleTimeString()}</span>
                </div>
                <div class="signal-reason">${signal.reason}</div>
            </div>
        `).join('');

        container.innerHTML = html;
    }

    formatUptime(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        return `${hours}小时${minutes}分钟`;
    }
}

// 页面加载完成后启动监控面板
document.addEventListener('DOMContentLoaded', () => {
    new MonitorDashboard();
});