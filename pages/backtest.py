"""
Backtest page: run Funding Rate Arb and Alt Market-Neutral strategies, view results.
"""
# flake8: noqa: E501
import sys
import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.backtest_data import load_funding_arb_data, load_alt_mn_data
from utils.backtest_funding_arb import run_funding_arb_backtest
from utils.backtest_alt_mn import run_alt_mn_backtest

st.set_page_config(page_title="Backtest", page_icon="📈", layout="wide")

st.title("📈 Backtest: Funding Arb & Alt Market-Neutral")
st.markdown("Запуск бэктестов двух стратегий из гайда. Настройте параметры и нажмите **Запустить**.")


def show_data_source(frame: pd.DataFrame) -> None:
    """Make the data origin explicit: synthetic or partially assumed data must never look real."""
    notes = frame.attrs.get("notes", [])
    if frame.attrs.get("synthetic"):
        st.warning("⚠️ SYNTHETIC / ASSUMED DATA — results are NOT a real backtest. " + " ".join(notes))
    else:
        st.caption("Data source: Binance (real historical data).")


tab1, tab2, tab3 = st.tabs(["Funding Rate Arb", "Alt Market-Neutral", "Справка"])

with tab1:
    st.subheader("Funding Rate Arbitrage")
    st.markdown("Delta-neutral: long spot, short perp. Вход при высоком funding, выход по basis stop-loss.")
    use_synth_1 = st.checkbox("Использовать синтетические данные (Funding Arb)", value=False,
                              help="Если API недоступен или для быстрого теста")
    c1, c2 = st.columns(2)
    with c1:
        start_fa = st.date_input("Начало периода (Funding Arb)", value=pd.to_datetime("2024-01-01"))
        end_fa = st.date_input("Конец периода (Funding Arb)", value=pd.to_datetime("2024-06-30"))
        capital_fa = st.number_input("Капитал (Funding Arb)", min_value=1000, value=100_000, step=5000)
        leverage_fa = st.number_input("Плечо (Funding Arb)", min_value=1.0, value=3.0, step=0.5)
        funding_threshold = st.number_input("Порог funding для входа (8h)", value=0.0001, format="%.5f",
                                            help="Открывать позицию, если funding_8h > порога")
        basis_sl = st.number_input("Basis stop-loss %", min_value=0.1, value=3.0, step=0.5)
    with c2:
        target_notional_pct = st.slider("Доля капитала в позиции %", 10, 90, 50)
        fee_spot_fa = st.number_input("Комиссия spot %", value=0.1, format="%.2f") / 100
        fee_perp_fa = st.number_input("Комиссия perp %", value=0.05, format="%.2f") / 100
        slippage_fa = st.number_input("Slippage %", value=0.02, format="%.2f") / 100
        min_funding_stay = st.number_input("Мин. funding для удержания (8h)", value=0.00005, format="%.5f")

    if st.button("Запустить бэктест (Funding Arb)", type="primary"):
        with st.spinner("Загрузка данных и расчёт..."):
            try:
                df = load_funding_arb_data(
                    symbol="BTC",
                    start_date=start_fa.strftime("%Y-%m-%d"),
                    end_date=end_fa.strftime("%Y-%m-%d"),
                    use_synthetic=use_synth_1,
                )
                if df is None or len(df) == 0:
                    st.error("Нет данных за выбранный период. Включите синтетические данные.")
                else:
                    equity, metrics = run_funding_arb_backtest(
                        df,
                        initial_capital=float(capital_fa),
                        leverage=float(leverage_fa),
                        funding_threshold=float(funding_threshold),
                        min_funding_to_stay=float(min_funding_stay),
                        basis_sl_pct=float(basis_sl),
                        target_notional_pct=float(target_notional_pct),
                        fee_spot=fee_spot_fa,
                        fee_perp=fee_perp_fa,
                        slippage_pct=slippage_fa,
                    )
                    st.success("Бэктест выполнен.")
                    show_data_source(df)

                    st.subheader("Результаты")
                    m1, m2, m3, m4, m5 = st.columns(5)
                    m1.metric("Доходность %", f"{metrics['total_return_pct']:.2f}")
                    m2.metric("Годовая волатильность %", f"{metrics['volatility_annual_pct']:.2f}")
                    m3.metric("Sharpe", f"{metrics['sharpe_ratio']:.2f}")
                    m4.metric("Max DD %", f"{metrics['max_drawdown_pct']:.2f}")
                    m5.metric("Итоговый капитал", f"${metrics['final_equity']:,.0f}")

                    st.markdown("**Декомпозиция PnL**")
                    dec = pd.DataFrame({
                        "Компонент": ["Funding", "Basis", "Комиссии"],
                        "PnL": [metrics["pnl_funding"], metrics["pnl_basis"], metrics["pnl_commissions"]],
                    })
                    st.dataframe(dec, use_container_width=True, hide_index=True)

                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=equity.index, y=equity.values,
                        mode="lines", name="Equity",
                        line=dict(color="#2ca02c", width=2), fill="tozeroy",
                    ))
                    fig.update_layout(
                        title="Кривая капитала (Funding Arb)",
                        xaxis_title="Дата",
                        yaxis_title="Капитал",
                        height=400, hovermode="x unified",
                    )
                    st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Ошибка: {e}")
                import traceback
                st.code(traceback.format_exc())

with tab2:
    st.subheader("Alt Market-Neutral")
    st.markdown("Long/short по моментуму (lookback), хедж по beta к BTC. Ребаланс раз в N дней.")
    use_synth_2 = st.checkbox(
        "Использовать синтетические данные (Alt MN)", value=False,
        help="Если API недоступен или для быстрого теста")
    symbols_default = "BTC,ETH,BNB,SOL,XRP,ADA,DOGE,AVAX,DOT,LINK"
    symbols_str = st.text_input("Символы (через запятую)", value=symbols_default)
    symbols_list = [s.strip().upper() for s in symbols_str.split(",") if s.strip()]
    if "BTC" not in symbols_list and not use_synth_2:
        symbols_list = ["BTC"] + [s for s in symbols_list if s != "BTC"]

    c1, c2 = st.columns(2)
    with c1:
        start_mn = st.date_input("Начало периода (Alt MN)", value=pd.to_datetime("2024-01-01"))
        end_mn = st.date_input("Конец периода (Alt MN)", value=pd.to_datetime("2024-06-30"))
        capital_mn = st.number_input("Капитал (Alt MN)", min_value=1000, value=100_000, step=5000)
        lookback = st.number_input("Lookback (дней) для моментума", min_value=5, value=30, step=5)
        quantile = st.slider("Квантиль long/short (доля сверху/снизу)", 0.1, 0.4, 0.2)
    with c2:
        rebalance_days = st.number_input("Ребаланс каждые N дней", min_value=1, value=7)
        fee_mn = st.number_input("Комиссия % (Alt MN)", value=0.1, format="%.2f") / 100
        slippage_mn = st.number_input("Slippage % (Alt MN)", value=0.1, format="%.2f") / 100
        beta_window = st.number_input("Окно для rolling beta (дней)", min_value=20, value=60)

    if st.button("Запустить бэктест (Alt Market-Neutral)", type="primary"):
        with st.spinner("Загрузка данных и расчёт..."):
            try:
                prices = load_alt_mn_data(
                    symbols_list,
                    start_date=start_mn.strftime("%Y-%m-%d"),
                    end_date=end_mn.strftime("%Y-%m-%d"),
                    use_synthetic=use_synth_2,
                )
                if prices is None or len(prices) < 100:
                    st.error("Мало данных. Увеличьте период или включите синтетические данные.")
                else:
                    equity, metrics = run_alt_mn_backtest(
                        prices,
                        initial_capital=float(capital_mn),
                        lookback_days=int(lookback),
                        quantile=float(quantile),
                        rebalance_days=int(rebalance_days),
                        fee=fee_mn,
                        slippage_pct=slippage_mn,
                        beta_window=int(beta_window),
                    )
                    st.success("Бэктест выполнен.")
                    show_data_source(prices)

                    st.subheader("Результаты")
                    m1, m2, m3, m4, m5 = st.columns(5)
                    m1.metric("Доходность %", f"{metrics['total_return_pct']:.2f}")
                    m2.metric("Годовая волатильность %", f"{metrics['volatility_annual_pct']:.2f}")
                    m3.metric("Sharpe", f"{metrics['sharpe_ratio']:.2f}")
                    m4.metric("Max DD %", f"{metrics['max_drawdown_pct']:.2f}")
                    m5.metric("Итоговый капитал", f"${metrics['final_equity']:,.0f}")

                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=equity.index, y=equity.values,
                        mode="lines", name="Equity",
                        line=dict(color="#1f77b4", width=2), fill="tozeroy",
                    ))
                    fig.update_layout(
                        title="Кривая капитала (Alt Market-Neutral)",
                        xaxis_title="Дата",
                        yaxis_title="Капитал",
                        height=400, hovermode="x unified",
                    )
                    st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Ошибка: {e}")
                import traceback
                st.code(traceback.format_exc())

with tab3:
    st.markdown("""
    - **Funding Rate Arb:** открываем delta-neutral (long spot, short perp) при funding выше порога;
      закрываем по basis stop-loss или при падении funding. Данные: spot и perp (Binance), funding rate.
    - **Alt Market-Neutral:** long топ по моментуму (lookback), short низ; хедж по beta к BTC;
      ребаланс раз в N дней. Данные: дневные цены по списку монет (Binance spot).
    - Для быстрого теста без API отметьте «Использовать синтетические данные».
    """)
