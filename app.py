"""Web Dashboard for Stocks Trading Bot - Fixed version"""
import streamlit as st
import sys
import os
import json
import math
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

st.set_page_config(
    page_title="📊 Stocks AI Dashboard",
    layout="wide",
    page_icon="📈"
)

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'state.json')


def safe_float(value, default=0.0):
    """Safely convert value to float"""
    if value is None:
        return default
    try:
        val = float(value)
        if math.isnan(val) or math.isinf(val):
            return default
        return val
    except (TypeError, ValueError):
        return default


def format_price(value):
    """Format price for display"""
    val = safe_float(value, 0.0)
    if val <= 0:
        return "N/A"
    return f"${val:.2f}"


def load_state():
    """Load state from JSON file"""
    if not os.path.exists(STATE_FILE):
        return None
    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Грешка при зареждане на state.json: {e}")
        return None


# ===== ИНИЦИАЛИЗАЦИЯ =====
if 'auto_refresh' not in st.session_state:
    st.session_state.auto_refresh = False

# ===== ЗАГЛАВИЕ =====
st.title("📊 Stocks AI Trading Dashboard")
st.markdown("---")

# ===== БУТОНИ =====
btn_col1, btn_col2 = st.columns(2)

with btn_col1:
    if st.button("🔄 Обнови Сега", use_container_width=True, type="primary"):
        st.rerun()

with btn_col2:
    if st.session_state.auto_refresh:
        if st.button("⏸️ Спри Авто-Обновяване", use_container_width=True, type="secondary"):
            st.session_state.auto_refresh = False
            st.rerun()
    else:
        if st.button("▶️ Авто Обновяване (10сек)", use_container_width=True):
            st.session_state.auto_refresh = True
            st.rerun()

st.markdown("---")

# ===== ЗАРЕЖДАНЕ НА ДАННИ =====
state = load_state()

if state is None:
    st.error("❌ Ботът не е стартиран или няма запазено състояние!")
    st.info("""
    💡 **Какво да направиш:**
    1. Отвори терминал
    2. `cd /Users/svetoslvstefnov/Desktop/SwiftUI/Форекс`
    3. `python bot_runner.py`
    4. Изчакай 1 минута и натисни 'Обнови Сега'
    """)
    st.stop()

# ===== ИЗВЛИЧАНЕ НА ДАННИ =====
balance = safe_float(state.get('balance', 0), 0.0)
initial_balance = safe_float(state.get('initial_balance', 10000), 10000)
positions = state.get('positions', {})
trades_history = state.get('trades_history', [])
last_updated = state.get('last_updated', 'Never')
last_prices = state.get('last_prices', {})

# Филтриране на затворени сделки
closed_trades = [t for t in trades_history if t.get('status') == 'CLOSED']
open_trades = [t for t in trades_history if t.get('status') == 'OPEN']

# Изчисляване на P&L
total_closed_pnl = sum(safe_float(t.get('pnl', 0), 0.0) for t in closed_trades)
total_unrealized_pnl = sum(
    safe_float(p.get('unrealized_pnl', 0), 0.0)
    for p in [
        {**pos, 'unrealized_pnl': (safe_float(last_prices.get(pos['symbol'], 0), 0) - safe_float(pos.get('entry_price', 0), 0)) * safe_float(pos.get('quantity', 0), 0)}
        for pos in positions.values()
    ]
)
total_pnl = total_closed_pnl + total_unrealized_pnl

# Win Rate
winning_trades = [t for t in closed_trades if safe_float(t.get('pnl', 0), 0) > 0]
losing_trades = [t for t in closed_trades if safe_float(t.get('pnl', 0), 0) < 0]
win_rate = (len(winning_trades) / len(closed_trades) * 100) if closed_trades else 0

# ===== СТАТУС =====
if st.session_state.auto_refresh:
    st.success(f"✅ Ботът е активен | 🔄 Автоматично обновяване ВКЛЮЧЕНО | Последно: {last_updated}")
else:
    st.success(f"✅ Ботът е активен | Последно обновяване: {last_updated}")

# ===== МЕТРИКИ =====
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric(
        "💰 Баланс",
        f"${balance:.2f}",
        delta=f"${balance - initial_balance:+.2f}"
    )

with col2:
    st.metric("📊 Отворени позиции", len(positions))

with col3:
    st.metric("📜 Затворени сделки", len(closed_trades))

with col4:
    pnl_delta = f"${total_closed_pnl:+.2f}" if total_closed_pnl != 0 else None
    st.metric(
        "📈 Реализиран P&L",
        f"${total_closed_pnl:.2f}",
        delta=pnl_delta
    )

with col5:
    st.metric(
        "🎯 Win Rate",
        f"{win_rate:.1f}%",
        delta=f"{len(winning_trades)}W / {len(losing_trades)}L"
    )

st.markdown("---")

# ===== ТАБОВЕ =====
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Отворени Позиции",
    "📜 История на Сделки",
    "💹 Текущи Цени",
    "📈 Статистика"
])

# ===== ТАБ 1: ОТВОРЕНИ ПОЗИЦИИ =====
with tab1:
    st.subheader("📊 Отворени Позиции")

    if not positions:
        st.info("ℹ️ Няма отворени позиции в момента.")
    else:
        for symbol, pos in positions.items():
            current_price = safe_float(last_prices.get(symbol, 0), 0)
            entry_price = safe_float(pos.get('entry_price', 0), 0)
            quantity = safe_float(pos.get('quantity', 0), 0)
            action = pos.get('action', 'BUY')

            if current_price <= 0 or entry_price <= 0:
                unrealized_pnl = 0.0
            elif action == 'BUY':
                unrealized_pnl = (current_price - entry_price) * quantity
            else:
                unrealized_pnl = (entry_price - current_price) * quantity

            emoji = '🟢' if action == 'BUY' else '🔴'
            pnl_emoji = '📈' if unrealized_pnl >= 0 else '📉'
            pnl_color = 'green' if unrealized_pnl >= 0 else 'red'

            with st.expander(f"{emoji} {symbol} - {action} {quantity} @ {format_price(entry_price)}", expanded=True):
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**Действие:** {action}")
                    st.write(f"**Влязъл на:** {pos.get('opened_at', 'N/A')}")
                    st.write(f"**Количество:** {quantity}")
                    st.write(f"**Входна цена:** {format_price(entry_price)}")

                with col2:
                    st.metric("Текуща цена", format_price(current_price))
                    st.metric(
                        f"{pnl_emoji} P&L",
                        f"${unrealized_pnl:.2f}",
                        delta=f"${unrealized_pnl:+.2f}"
                    )
                    st.write(f"**Стоп Лос:** {format_price(pos.get('stop_loss', 0))}")
                    st.write(f"**Тейк Профит:** {format_price(pos.get('take_profit', 0))}")

# ===== ТАБ 2: ИСТОРИЯ НА СДЕЛКИ =====
with tab2:
    st.subheader("📜 История на Сделки")

    if not closed_trades:
        st.info("ℹ️ Няма затворени сделки.")
    else:
        # Обща статистика
        col1, col2, col3 = st.columns(3)

        with col1:
            pnl_class = "positive" if total_closed_pnl >= 0 else "negative"
            st.metric("💵 Общ P&L", f"${total_closed_pnl:.2f}")

        with col2:
            st.metric("🏆 Печеливши", len(winning_trades))

        with col3:
            st.metric("💔 Загубени", len(losing_trades))

        st.markdown("---")

        # Списък със затворени сделки
        for trade in reversed(closed_trades):
            pnl = safe_float(trade.get('pnl', 0), 0.0)
            symbol = trade.get('symbol', 'N/A')
            action = trade.get('action', 'N/A')
            entry_price = safe_float(trade.get('entry_price', 0), 0.0)
            exit_price = safe_float(trade.get('exit_price', 0), 0.0)
            quantity = safe_float(trade.get('quantity', 0), 0.0)

            emoji = "✅" if pnl >= 0 else "❌"
            pnl_emoji = "📈" if pnl >= 0 else "📉"

            with st.expander(f"{emoji} #{trade.get('id', 0)} - {symbol} {action} | P&L: ${pnl:+.2f}"):
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**Акция:** {symbol}")
                    st.write(f"**Действие:** {action}")
                    st.write(f"**Количество:** {quantity}")
                    st.write(f"**Входна цена:** {format_price(entry_price)}")

                with col2:
                    st.write(f"**Изходна цена:** {format_price(exit_price)}")
                    st.write(f"**Затворена на:** {trade.get('closed_at', 'N/A')}")
                    st.metric(f"{pnl_emoji} P&L", f"${pnl:.2f}", delta=f"${pnl:+.2f}")

                    if pnl >= 0:
                        st.success(f"✅ Печалба: ${pnl:.2f}")
                    else:
                        st.error(f"❌ Загуба: ${abs(pnl):.2f}")

# ===== ТАБ 3: ТЕКУЩИ ЦЕНИ =====
with tab3:
    st.subheader("💹 Текущи Цени")

    if not last_prices:
        st.info("ℹ️ Няма текущи цени.")
    else:
        cols = st.columns(3)
        for i, (symbol, price) in enumerate(last_prices.items()):
            with cols[i % 3]:
                st.metric(symbol, format_price(price))

# ===== ТАБ 4: СТАТИСТИКА =====
with tab4:
    st.subheader("📈 Статистика")

    col1, col2 = st.columns(2)

    with col1:
        st.write("**📊 Обща статистика:**")
        st.write(f"- Начален баланс: ${initial_balance:.2f}")
        st.write(f"- Текущ баланс: ${balance:.2f}")
        st.write(f"- Общ P&L: ${total_pnl:.2f}")
        st.write(f"- Реализиран P&L: ${total_closed_pnl:.2f}")
        st.write(f"- Нереализиран P&L: ${total_unrealized_pnl:.2f}")

    with col2:
        st.write("**🎯 Търговска статистика:**")
        st.write(f"- Общо сделки: {len(trades_history)}")
        st.write(f"- Отворени: {len(open_trades)}")
        st.write(f"- Затворени: {len(closed_trades)}")
        st.write(f"- Печеливши: {len(winning_trades)}")
        st.write(f"- Загубени: {len(losing_trades)}")
        st.write(f"- Win Rate: {win_rate:.1f}%")

    if closed_trades:
        st.markdown("---")
        st.write("**📈 Разпределение на печалби/загуби:**")

        # Най-добра и най-лоша сделка
        best_trade = max(closed_trades, key=lambda t: safe_float(t.get('pnl', 0), 0))
        worst_trade = min(closed_trades, key=lambda t: safe_float(t.get('pnl', 0), 0))

        col1, col2 = st.columns(2)

        with col1:
            st.success(f"**🏆 Най-добра сделка:**")
            st.write(f"- {best_trade.get('symbol')} {best_trade.get('action')}")
            st.write(f"- P&L: ${safe_float(best_trade.get('pnl', 0), 0):.2f}")

        with col2:
            st.error(f"**💔 Най-лоша сделка:**")
            st.write(f"- {worst_trade.get('symbol')} {worst_trade.get('action')}")
            st.write(f"- P&L: ${safe_float(worst_trade.get('pnl', 0), 0):.2f}")

# ===== FOOTER =====
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray; font-size: 12px;'>"
    "🤖 Stocks AI Trading Bot v4.0 | Paper Trading Mode | Данните се обновяват от бота"
    "</div>",
    unsafe_allow_html=True
)

# ===== АВТОМАТИЧНО ОБНОВЯВАНЕ =====
if st.session_state.auto_refresh:
    import time
    time.sleep(10)
    st.rerun()