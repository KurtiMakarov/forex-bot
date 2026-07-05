"""
Live readiness gate:
- Reads JSONL journal
- Computes KPIs from CLOSED positions
- Decides if live trading can be unlocked
"""

from __future__ import annotations
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Tuple


@dataclass
class ReadinessResult:
    ready: bool
    reason: str
    stats: Dict[str, float]
    sample_size: int


def _parse_ts(ts: str) -> datetime | None:
    try:
        # supports "...Z"
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        return datetime.fromisoformat(ts).astimezone(timezone.utc)
    except Exception:
        return None


def _safe_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default


def _max_drawdown(equity_curve: List[float]) -> float:
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]
    max_dd = 0.0
    for v in equity_curve:
        if v > peak:
            peak = v
        if peak > 0:
            dd = (peak - v) / peak
            if dd > max_dd:
                max_dd = dd
    return max_dd


def _profit_factor(pnls: List[float]) -> float:
    gross_profit = sum(p for p in pnls if p > 0)
    gross_loss = abs(sum(p for p in pnls if p < 0))
    if gross_loss == 0:
        return 999.0 if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def _win_rate(pnls: List[float]) -> float:
    if not pnls:
        return 0.0
    wins = sum(1 for p in pnls if p > 0)
    return wins / len(pnls)


def evaluate_live_readiness(
    journal_path: str,
    min_closed_trades: int = 30,
    lookback_days: int = 30,
    min_profit_factor: float = 1.20,
    max_drawdown_limit: float = 0.05,
    min_win_rate: float = 0.40,
    max_single_loss_r: float = 1.0,   # reserved if you later log R-multiples
) -> ReadinessResult:
    if not os.path.exists(journal_path):
        return ReadinessResult(
            ready=False,
            reason=f"Journal not found: {journal_path}",
            stats={},
            sample_size=0
        )

    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)

    closed_events: List[Dict[str, Any]] = []
    balance_events: List[Dict[str, Any]] = []

    with open(journal_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue

            ts = _parse_ts(str(rec.get("ts", "")))
            if ts is None or ts < cutoff:
                continue

            et = rec.get("event_type", "")
            if et == "position_closed":
                closed_events.append(rec)
            elif et == "balance":
                balance_events.append(rec)

    pnls = [_safe_float(e.get("pnl"), 0.0) for e in closed_events]
    sample_size = len(pnls)

    if sample_size < min_closed_trades:
        return ReadinessResult(
            ready=False,
            reason=f"Not enough closed trades: {sample_size}/{min_closed_trades}",
            stats={"closed_trades": sample_size},
            sample_size=sample_size
        )

    pf = _profit_factor(pnls)
    wr = _win_rate(pnls)

    equity_curve: List[float] = []
    for b in balance_events:
        equity_curve.append(_safe_float(b.get("balance"), 0.0))
    mdd = _max_drawdown(equity_curve) if equity_curve else 1.0

    stats = {
        "closed_trades": float(sample_size),
        "profit_factor": float(pf),
        "win_rate": float(wr),
        "max_drawdown": float(mdd),
    }

    checks: List[Tuple[bool, str]] = [
        (pf >= min_profit_factor, f"PF {pf:.2f} < {min_profit_factor:.2f}"),
        (wr >= min_win_rate, f"WinRate {wr:.2%} < {min_win_rate:.2%}"),
        (mdd <= max_drawdown_limit, f"MaxDD {mdd:.2%} > {max_drawdown_limit:.2%}"),
    ]

    failed = [msg for ok, msg in checks if not ok]
    if failed:
        return ReadinessResult(
            ready=False,
            reason="; ".join(failed),
            stats=stats,
            sample_size=sample_size
        )

    return ReadinessResult(
        ready=True,
        reason="All live-readiness checks passed",
        stats=stats,
        sample_size=sample_size
    )