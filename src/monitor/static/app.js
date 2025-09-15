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
        return (
            <div className="container">
                <div className="flex justify-center items-center h-screen">
                    <div className="text-xl">正在加载监控数据...</div>
                </div>
            </div>
        );
    }

    return (
        <div className="container">
            {/* Header */}
            <header>
                <h1>🚀 量化交易监控面板</h1>
                <div className="status-bar">
                    <span className={`status-indicator ${snapshot.system_status.toLowerCase().replace(/[^a-z]/g, '')}`}>
                        {snapshot.system_status}
                    </span>
                    <span>最后更新: {lastUpdate}</span>
                </div>
            </header>

            {/* Dashboard Grid */}
            <div className="dashboard-grid">
                {/* 系统概览 */}
                <div className="card overview">
                    <h2>📊 系统概览</h2>
                    <div className="metrics">
                        <div className="metric">
                            <span className="metric-value">{snapshot.total_signals}</span>
                            <span className="metric-label">今日信号</span>
                        </div>
                        <div className="metric">
                            <span className="metric-value">{snapshot.active_positions}</span>
                            <span className="metric-label">活跃持仓</span>
                        </div>
                        <div className="metric">
                            <span
                                className="metric-value"
                                style={{color: snapshot.daily_pnl >= 0 ? '#27ae60' : '#e74c3c'}}
                            >
                                ${snapshot.daily_pnl.toFixed(2)}
                            </span>
                            <span className="metric-label">今日PnL</span>
                        </div>
                    </div>
                </div>

                {/* 连接状态 */}
                <div className="card connections">
                    <h2>🔗 连接状态</h2>
                    <div className="connection-status">
                        <div className="connection">
                            <span className={`connection-indicator ${snapshot.data_feed_connected ? 'connected' : 'disconnected'}`}>
                                ●
                            </span>
                            <span>数据源</span>
                        </div>
                        <div className="connection">
                            <span className={`connection-indicator ${snapshot.trading_api_connected ? 'connected' : 'disconnected'}`}>
                                ●
                            </span>
                            <span>交易API</span>
                        </div>
                    </div>
                </div>

                {/* 系统性能 */}
                <div className="card performance">
                    <h2>⚡ 系统性能</h2>
                    <div className="resource-usage">
                        <div className="resource">
                            <span>CPU使用率</span>
                            <span>{snapshot.cpu_usage}%</span>
                        </div>
                        <div className="resource">
                            <span>内存使用率</span>
                            <span>{snapshot.memory_usage}%</span>
                        </div>
                        <div className="resource">
                            <span>运行时间</span>
                            <span>{formatUptime(snapshot.uptime_seconds)}</span>
                        </div>
                    </div>
                </div>

                {/* 股票状态 */}
                <div className="card symbols">
                    <h2>📈 股票状态</h2>
                    <div className="symbols-list">
                        {Object.keys(snapshot.symbols).length === 0 ? (
                            <p>暂无股票数据</p>
                        ) : (
                            Object.values(snapshot.symbols).map((symbol, index) => (
                                <div key={index} className="symbol-item">
                                    <div>
                                        <span className="symbol-name">{symbol.symbol}</span>
                                        <span className={`symbol-trend trend-${symbol.trend.toLowerCase()}`}>
                                            {symbol.trend}
                                        </span>
                                    </div>
                                    <div>
                                        <span className="symbol-price">
                                            ${symbol.current_price ? symbol.current_price.toFixed(2) : '--'}
                                        </span>
                                        {symbol.price_change_pct && (
                                            <span style={{color: symbol.price_change_pct >= 0 ? '#27ae60' : '#e74c3c'}}>
                                                {symbol.price_change_pct.toFixed(2)}%
                                            </span>
                                        )}
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>

                {/* 最新信号 */}
                <div className="card signals">
                    <h2>🎯 最新信号</h2>
                    <div className="signals-list">
                        {signals.length === 0 ? (
                            <p>暂无信号数据</p>
                        ) : (
                            signals.slice(0, 10).map((signal, index) => (
                                <div key={index} className="signal-item">
                                    <div className="signal-header">
                                        <span className={`signal-type signal-${signal.signal_type.toLowerCase()}`}>
                                            {signal.signal_type}
                                        </span>
                                        <span>{signal.symbol}</span>
                                        <span>${signal.price.toFixed(2)}</span>
                                        <span>{new Date(signal.timestamp).toLocaleTimeString()}</span>
                                    </div>
                                    <div className="signal-reason">{signal.reason}</div>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

// 渲染应用
const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<MonitorDashboard />);