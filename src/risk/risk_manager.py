"""
Centralized risk management rules shared across the strategy pipeline.
"""

from dataclasses import dataclass
from typing import Optional

from models.strategy_data import TradingSignal, MarketContext


@dataclass(frozen=True)
class RiskDecision:
    """Result of risk filtering."""

    signal: Optional[TradingSignal]
    reason: Optional[str] = None
    adjusted: bool = False


class RiskManager:
    """Applies common risk filters to trading signals."""

    @staticmethod
    def apply_risk_filters(
        signal: Optional[TradingSignal],
        context: Optional[MarketContext],
        last_signal: Optional[TradingSignal] = None,
    ) -> RiskDecision:
        if not signal or not context:
            return RiskDecision(signal=signal)

        # Volatility guard
        if context.volatility > 5.0:
            return RiskDecision(signal=None, reason="volatility_high")

        adjusted_signal = signal
        adjusted = False

        # Volume-based confidence adjustment
        if context.volume_profile == "LOW" and not signal.reason.endswith("(成交量偏低)"):
            adjusted_signal = TradingSignal(
                symbol=signal.symbol,
                signal_type=signal.signal_type,
                confidence=signal.confidence * 0.7,
                price=signal.price,
                timestamp=signal.timestamp,
                reason=f"{signal.reason} (成交量偏低)",
            )
            adjusted = True

        # Throttle repetitive signals
        if (
            last_signal
            and adjusted_signal.signal_type == last_signal.signal_type
            and (adjusted_signal.timestamp - last_signal.timestamp).total_seconds() < 300
        ):
            return RiskDecision(signal=None, reason="duplicate_signal")

        return RiskDecision(signal=adjusted_signal, adjusted=adjusted)
