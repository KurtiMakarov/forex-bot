import os
import json
from datetime import datetime, timezone
import streamlit as st
import pandas as pd

try:
    from utils.live_readiness import evaluate_live_readiness
except Exception:
    evaluate_live_readiness = None

st.set_page_config(page_title="Stocks AI Dashboard", page_icon="📊", layout="wide")

JOURNAL_PATH = "journal/trades.jsonl"
STATE_PATH = "state.json"
EMERGENCY_STOP_FILE = "runtime/EMERGENCY_STOP"


def _safe_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default


def _parse_ts(ts):
    try:
        if isinstance(ts, str) and ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        return datetime.fromisoformat(ts).astimezone(timezone.utc)
    except Exception:
        return None


@st.cache_data(ttl=5)
def load_journal(path: str):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                pass
    return rows


@st.cache_data(ttl=5)
def load_state(path: str):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def derive_metrics(journal_rows):
    balance = 0.0
    closed_trades = 0
    realized_pnl = 0.0
    wins, losses = 0, 0
    open_symbols = set()
    last_ts = None

    for r in journal_rows:
        ts = _parse_ts(r.get("ts"))
        if ts and (last_ts is None or ts > last_ts):
            last_ts = ts

        et = r.get("event_type")
        if et == "balance":
            balance = _safe_float(r.get("balance"), balance)
        elif et == "order_executed":
            sym = r.get("symbol")
            if sym:
                open_symbols.add(sym)
        elif et == "position_closed":
            sym = r.get("symbol")
            if sym in open_symbols:
                open_symbols.remove(sym)
            pnl = _safe_float(r.get("pnl"))
            realized_pnl += pnl
            closed_trades += 1
            if pnl > 0:
                wins += 1
            elif pnl < 0:
                losses += 1

    wr = (wins / (wins + losses)) if (wins + losses) > 0 else 0.0
    return {
        "balance": balance,
        "open_positions": len(open_symbols),
        "closed_trades": closed_trades,
        "realized_pnl": realized_pnl,
        "wins": wins,
        "losses": losses,
        "win_rate": wr,
        "last_ts": last_ts.isoformat() if last_ts else "N/A",
    }


def get_live_readiness_result():
    if evaluate_live_readiness is None:
        return None, "utils/live_readiness.py липсва"

    if not os.path.exists(JOURNAL_PATH):
        return None, f"Липсва journal: {JOURNAL_PATH}"

    result = evaluate_live_readiness(
        journal_path=JOURNAL_PATH,
        min_closed_trades=30,
        lookback_days=30,
        min_profit_factor=1.20,
        max_drawdown_limit=0.05,
        min_win_rate=0.40
    )
    return result, None


def ensure_runtime_dir():
    os.makedirs("runtime", exist_ok=True)


def emergency_is_active():
    return os.path.exists(EMERGENCY_STOP_FILE)


def set_emergency_stop(active: bool):
    ensure_runtime_dir()
    if active:
        with open(EMERGENCY_STOP_FILE, "w", encoding="utf-8") as f:
            f.write(datetime.utcnow().isoformat() + "Z")
    else:
        if os.path.exists(EMERGENCY_STOP_FILE):
            os.remove(EMERGENCY_STOP_FILE)


def show_top_safety_banner(readiness_result):
    if emergency_is_active():
        st.error("🛑 EMERGENCY STOP ACTIVE — trading трябва да е блокиран.")
        return

    if readiness_result is None:
        st.warning("⚠️ LIVE readiness status unknown.")
        return

    if readiness_result.ready:
        st.success("✅ LIVE READY (по KPI). Въпреки това остави allow_live_trading=false, докато не решиш.")
    else:
        st.error("🔒 LIVE LOCKED — условията за live не са покрити.")


def show_live_readiness(readiness_result, readiness_err):
    st.subheader("🔐 Live Readiness")

    if readiness_err:
        st.warning(readiness_err)
        return

    if readiness_result.ready:
        st.success("✅ READY for live")
    else:
        st.error("🔒 NOT READY for live")

    st.caption(readiness_result.reason)
    stats = readiness_result.stats or {}
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Closed Trades", int(stats.get("closed_trades", readiness_result.sample_size or 0)))
    c2.metric("Profit Factor", f"{stats.get('profit_factor', 0.0):.2f}")
    c3.metric("Max Drawdown", f"{stats.get('max_drawdown', 0.0)*100:.2f}%")
    c4.metric("Win Rate", f"{stats.get('win_rate', 0.0)*100:.2f}%")


def show_emergency_controls():
    st.subheader("🧯 Emergency Controls")
    c1, c2 = st.columns(2)

    with c1:
        if st.button("🛑 ACTIVATE EMERGENCY STOP", use_container_width=True):
            set_emergency_stop(True)
            st.success("Emergency stop ACTIVATED")
            st.rerun()

    with c2:
        if st.button("✅ CLEAR EMERGENCY STOP", use_container_width=True):
            set_emergency_stop(False)
            st.success("Emergency stop CLEARED")
            st.rerun()

    st.caption(f"Флаг файл: `{EMERGENCY_STOP_FILE}` | active={emergency_is_active()}")


def main():
    st.title("📊 Stocks AI Trading Dashboard")
    st.markdown("---")

    readiness_result, readiness_err = get_live_readiness_result()
    show_top_safety_banner(readiness_result)

    cbtn1, cbtn2 = st.columns(2)
    with cbtn1:
        if st.button("🔄 Обнови Сега", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    with cbtn2:
        pause_auto = st.toggle("⏸️ Спри Авто-Обновяване", value=False)

    journal_rows = load_journal(JOURNAL_PATH)
    state = load_state(STATE_PATH)
    m = derive_metrics(journal_rows)

    st.success(
        f"✅ Ботът е активен | {'⏸️ Авто-обновяване ИЗКЛЮЧЕНО' if pause_auto else '🔄 Авто-обновяване ВКЛЮЧЕНО'} | Последно: {m['last_ts']}"
    )

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("💰 Баланс", f"${m['balance']:.2f}")
    c2.metric("📊 Отворени позиции", f"{m['open_positions']}")
    c3.metric("📜 Затворени сделки", f"{m['closed_trades']}")
    c4.metric("📈 Реализиран P&L", f"${m['realized_pnl']:.2f}")
    c5.metric("🎯 Win Rate", f"{m['win_rate']*100:.1f}% ({m['wins']}W/{m['losses']}L)")

    st.markdown("---")
    show_live_readiness(readiness_result, readiness_err)

    st.markdown("---")
    show_emergency_controls()

    st.markdown("---")
    tab1, tab2, tab3 = st.tabs(["📜 Journal", "📂 State", "📈 PnL Curve"])

    with tab1:
        if journal_rows:
            st.dataframe(pd.DataFrame(journal_rows[-200:]), use_container_width=True)
        else:
            st.info("Няма journal записи.")

    with tab2:
        st.json(state if state else {"info": "state.json не е наличен/празен"})

    with tab3:
        closed = [r for r in journal_rows if r.get("event_type") == "position_closed"]
        if not closed:
            st.info("Няма затворени сделки.")
        else:
            df = pd.DataFrame(closed)
            df["pnl"] = pd.to_numeric(df.get("pnl", 0), errors="coerce").fillna(0.0)
            df["cum_pnl"] = df["pnl"].cumsum()
            st.line_chart(df["cum_pnl"])
            st.dataframe(df.tail(200), use_container_width=True)

    if not pause_auto:
        st.caption("Обновяване на всеки 5 сек (натисни Refresh/Rerun при нужда).")


if __name__ == "__main__":
    main()