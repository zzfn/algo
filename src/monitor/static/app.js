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
            <div className="max-w-7xl mx-auto p-5">
                <div className="flex justify-center items-center h-screen">
                    <div className="text-xl text-gray-200">正在加载监控数据...</div>
                </div>
            </div>
        );
    }

    return (
        <div className="max-w-7xl mx-auto p-5">
            {/* Header */}
            <header className="bg-slate-800 rounded-xl p-5 mb-5 flex flex-col md:flex-row justify-between items-center gap-2.5">
                <h1 className="text-slate-400 text-2xl font-semibold">🚀 量化交易监控面板</h1>
                <div className="flex gap-5 items-center">
                    <span className={`px-3 py-1 rounded-full text-xs font-bold text-white ${
                        snapshot.system_status.toLowerCase().includes('running') ? 'bg-green-600' :
                        snapshot.system_status.toLowerCase().includes('stopped') ? 'bg-red-600' :
                        'bg-yellow-600'
                    }`}>
                        {snapshot.system_status}
                    </span>
                    <span className="text-gray-300">最后更新: {lastUpdate}</span>
                </div>
            </header>

            {/* Dashboard Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                {/* 系统概览 */}
                <div className="bg-slate-800 rounded-xl p-5 border border-slate-700">
                    <h2 className="mb-4 text-red-400 text-lg font-semibold">📊 系统概览</h2>
                    <div className="flex flex-col md:flex-row justify-around gap-2.5">
                        <div className="text-center">
                            <span className="block text-2xl font-bold text-green-600">{snapshot.total_signals}</span>
                            <span className="block text-xs text-gray-400 mt-1">今日信号</span>
                        </div>
                        <div className="text-center">
                            <span className="block text-2xl font-bold text-green-600">{snapshot.active_positions}</span>
                            <span className="block text-xs text-gray-400 mt-1">活跃持仓</span>
                        </div>
                        <div className="text-center">
                            <span className={`block text-2xl font-bold ${snapshot.daily_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                ${snapshot.daily_pnl.toFixed(2)}
                            </span>
                            <span className="block text-xs text-gray-400 mt-1">今日PnL</span>
                        </div>
                    </div>
                </div>

                {/* 连接状态 */}
                <div className="bg-slate-800 rounded-xl p-5 border border-slate-700">
                    <h2 className="mb-4 text-red-400 text-lg font-semibold">🔗 连接状态</h2>
                    <div className="flex gap-5">
                        <div className="flex items-center gap-2">
                            <span className={`text-base ${snapshot.data_feed_connected ? 'text-green-600' : 'text-red-600'}`}>
                                ●
                            </span>
                            <span className="text-gray-200">数据源</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <span className={`text-base ${snapshot.trading_api_connected ? 'text-green-600' : 'text-red-600'}`}>
                                ●
                            </span>
                            <span className="text-gray-200">交易API</span>
                        </div>
                    </div>
                </div>

                {/* 系统性能 */}
                <div className="bg-slate-800 rounded-xl p-5 border border-slate-700">
                    <h2 className="mb-4 text-red-400 text-lg font-semibold">⚡ 系统性能</h2>
                    <div className="flex flex-col gap-2.5">
                        <div className="flex justify-between items-center">
                            <span className="text-gray-200">CPU使用率</span>
                            <span className="text-gray-200">{snapshot.cpu_usage}%</span>
                        </div>
                        <div className="flex justify-between items-center">
                            <span className="text-gray-200">内存使用率</span>
                            <span className="text-gray-200">{snapshot.memory_usage}%</span>
                        </div>
                        <div className="flex justify-between items-center">
                            <span className="text-gray-200">运行时间</span>
                            <span className="text-gray-200">{formatUptime(snapshot.uptime_seconds)}</span>
                        </div>
                    </div>
                </div>

                {/* 股票状态 */}
                <div className="bg-slate-800 rounded-xl p-5 border border-slate-700">
                    <h2 className="mb-4 text-red-400 text-lg font-semibold">📈 股票状态</h2>
                    <div className="max-h-72 overflow-y-auto">
                        {Object.keys(snapshot.symbols).length === 0 ? (
                            <p className="text-gray-400">暂无股票数据</p>
                        ) : (
                            Object.values(snapshot.symbols).map((symbol, index) => (
                                <div key={index} className="flex justify-between items-center p-2.5 border-b border-slate-700 bg-slate-700 mb-2 rounded-lg">
                                    <div className="flex items-center gap-2">
                                        <span className="font-bold text-red-400">{symbol.symbol}</span>
                                        <span className={`text-xs px-1.5 py-0.5 rounded-lg text-white ${
                                            symbol.trend.toLowerCase() === 'uptrend' ? 'bg-green-600' :
                                            symbol.trend.toLowerCase() === 'downtrend' ? 'bg-red-600' :
                                            'bg-yellow-600'
                                        }`}>
                                            {symbol.trend}
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <span className="text-green-600">
                                            ${symbol.current_price ? symbol.current_price.toFixed(2) : '--'}
                                        </span>
                                        {symbol.price_change_pct && (
                                            <span className={symbol.price_change_pct >= 0 ? 'text-green-600' : 'text-red-600'}>
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
                <div className="bg-slate-800 rounded-xl p-5 border border-slate-700">
                    <h2 className="mb-4 text-red-400 text-lg font-semibold">🎯 最新信号</h2>
                    <div className="max-h-72 overflow-y-auto">
                        {signals.length === 0 ? (
                            <p className="text-gray-400">暂无信号数据</p>
                        ) : (
                            signals.slice(0, 10).map((signal, index) => (
                                <div key={index} className="p-2 border-b border-slate-700 text-xs">
                                    <div className="flex justify-between items-center mb-1">
                                        <span className={`px-1.5 py-0.5 rounded text-white font-bold ${
                                            signal.signal_type.toLowerCase() === 'buy' ? 'bg-green-600' : 'bg-red-600'
                                        }`}>
                                            {signal.signal_type}
                                        </span>
                                        <span className="text-gray-200">{signal.symbol}</span>
                                        <span className="text-gray-200">${signal.price.toFixed(2)}</span>
                                        <span className="text-gray-200">{new Date(signal.timestamp).toLocaleTimeString()}</span>
                                    </div>
                                    <div className="text-gray-400 text-xs">{signal.reason}</div>
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