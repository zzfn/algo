const { useState, useEffect } = React;

// 监控面板主组件
function MonitorDashboard() {
    const [snapshot, setSnapshot] = useState(null);
    const [signals, setSignals] = useState([]);
    const [lastUpdate, setLastUpdate] = useState('--');
    const [isUpdating, setIsUpdating] = useState(false);

    // 获取监控快照
    const fetchSnapshot = async () => {
        try {
            const response = await fetch('/api/snapshot');
            const data = await response.json();
            setSnapshot(data);
            setLastUpdate(new Date(data.timestamp).toLocaleTimeString());
        } catch (error) {
            console.error('获取监控快照失败:', error);
        }
    };

    // 获取信号历史
    const fetchSignals = async () => {
        try {
            const response = await fetch('/api/signals?limit=10');
            const data = await response.json();
            setSignals(data);
        } catch (error) {
            console.error('获取信号历史失败:', error);
        }
    };

    // 更新数据
    const updateData = async () => {
        if (isUpdating) return;
        setIsUpdating(true);

        try {
            await Promise.all([fetchSnapshot(), fetchSignals()]);
        } catch (error) {
            console.error('更新数据失败:', error);
        } finally {
            setIsUpdating(false);
        }
    };

    // 格式化运行时间
    const formatUptime = (seconds) => {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        return `${hours}小时${minutes}分钟`;
    };

    // 初始化和定时更新
    useEffect(() => {
        updateData();
        const interval = setInterval(updateData, 2000);
        return () => clearInterval(interval);
    }, []);

    if (!snapshot) {
        return React.createElement('div', { className: 'container' },
            React.createElement('div', { className: 'flex justify-center items-center h-screen' },
                React.createElement('div', { className: 'text-xl' }, '正在加载监控数据...')
            )
        );
    }

    return React.createElement('div', { className: 'container' },
        // Header
        React.createElement('header', null,
            React.createElement('h1', null, '🚀 量化交易监控面板'),
            React.createElement('div', { className: 'status-bar' },
                React.createElement('span', {
                    className: `status-indicator ${snapshot.system_status.toLowerCase().replace(/[^a-z]/g, '')}`
                }, snapshot.system_status),
                React.createElement('span', null, `最后更新: ${lastUpdate}`)
            )
        ),

        // Dashboard Grid
        React.createElement('div', { className: 'dashboard-grid' },
            // 系统概览
            React.createElement('div', { className: 'card overview' },
                React.createElement('h2', null, '📊 系统概览'),
                React.createElement('div', { className: 'metrics' },
                    React.createElement('div', { className: 'metric' },
                        React.createElement('span', { className: 'metric-value' }, snapshot.total_signals),
                        React.createElement('span', { className: 'metric-label' }, '今日信号')
                    ),
                    React.createElement('div', { className: 'metric' },
                        React.createElement('span', { className: 'metric-value' }, snapshot.active_positions),
                        React.createElement('span', { className: 'metric-label' }, '活跃持仓')
                    ),
                    React.createElement('div', { className: 'metric' },
                        React.createElement('span', {
                            className: 'metric-value',
                            style: { color: snapshot.daily_pnl >= 0 ? '#27ae60' : '#e74c3c' }
                        }, `$${snapshot.daily_pnl.toFixed(2)}`),
                        React.createElement('span', { className: 'metric-label' }, '今日PnL')
                    )
                )
            ),

            // 连接状态
            React.createElement('div', { className: 'card connections' },
                React.createElement('h2', null, '🔗 连接状态'),
                React.createElement('div', { className: 'connection-status' },
                    React.createElement('div', { className: 'connection' },
                        React.createElement('span', {
                            className: `connection-indicator ${snapshot.data_feed_connected ? 'connected' : 'disconnected'}`
                        }, '●'),
                        React.createElement('span', null, '数据源')
                    ),
                    React.createElement('div', { className: 'connection' },
                        React.createElement('span', {
                            className: `connection-indicator ${snapshot.trading_api_connected ? 'connected' : 'disconnected'}`
                        }, '●'),
                        React.createElement('span', null, '交易API')
                    )
                )
            ),

            // 系统性能
            React.createElement('div', { className: 'card performance' },
                React.createElement('h2', null, '⚡ 系统性能'),
                React.createElement('div', { className: 'resource-usage' },
                    React.createElement('div', { className: 'resource' },
                        React.createElement('span', null, 'CPU使用率'),
                        React.createElement('span', null, `${snapshot.cpu_usage}%`)
                    ),
                    React.createElement('div', { className: 'resource' },
                        React.createElement('span', null, '内存使用率'),
                        React.createElement('span', null, `${snapshot.memory_usage}%`)
                    ),
                    React.createElement('div', { className: 'resource' },
                        React.createElement('span', null, '运行时间'),
                        React.createElement('span', null, formatUptime(snapshot.uptime_seconds))
                    )
                )
            ),

            // 股票状态
            React.createElement('div', { className: 'card symbols' },
                React.createElement('h2', null, '📈 股票状态'),
                React.createElement('div', { className: 'symbols-list' },
                    Object.keys(snapshot.symbols).length === 0
                        ? React.createElement('p', null, '暂无股票数据')
                        : Object.values(snapshot.symbols).map((symbol, index) =>
                            React.createElement('div', { key: index, className: 'symbol-item' },
                                React.createElement('div', null,
                                    React.createElement('span', { className: 'symbol-name' }, symbol.symbol),
                                    React.createElement('span', {
                                        className: `symbol-trend trend-${symbol.trend.toLowerCase()}`
                                    }, symbol.trend)
                                ),
                                React.createElement('div', null,
                                    React.createElement('span', { className: 'symbol-price' },
                                        `$${symbol.current_price ? symbol.current_price.toFixed(2) : '--'}`
                                    ),
                                    symbol.price_change_pct && React.createElement('span', {
                                        style: { color: symbol.price_change_pct >= 0 ? '#27ae60' : '#e74c3c' }
                                    }, `${symbol.price_change_pct.toFixed(2)}%`)
                                )
                            )
                        )
                )
            ),

            // 最新信号
            React.createElement('div', { className: 'card signals' },
                React.createElement('h2', null, '🎯 最新信号'),
                React.createElement('div', { className: 'signals-list' },
                    signals.length === 0
                        ? React.createElement('p', null, '暂无信号数据')
                        : signals.slice(0, 10).map((signal, index) =>
                            React.createElement('div', { key: index, className: 'signal-item' },
                                React.createElement('div', { className: 'signal-header' },
                                    React.createElement('span', {
                                        className: `signal-type signal-${signal.signal_type.toLowerCase()}`
                                    }, signal.signal_type),
                                    React.createElement('span', null, signal.symbol),
                                    React.createElement('span', null, `$${signal.price.toFixed(2)}`),
                                    React.createElement('span', null, new Date(signal.timestamp).toLocaleTimeString())
                                ),
                                React.createElement('div', { className: 'signal-reason' }, signal.reason)
                            )
                        )
                )
            )
        )
    );
}

// 页面加载完成后启动
document.addEventListener('DOMContentLoaded', () => {
    ReactDOM.render(React.createElement(MonitorDashboard), document.getElementById('root'));
});