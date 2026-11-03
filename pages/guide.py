"""
Guide page - Backtest production guide (Funding Arb & Alt Market-Neutral).
"""
# flake8: noqa: E501
import streamlit as st

st.set_page_config(page_title="Backtest Guide", page_icon="📖", layout="wide")

st.title("📖 Backtest Guide: Funding Arb & Alt Market-Neutral")

st.markdown("""
Практический гайд «под продакшн» по двум стратегиям: funding arb и alt market-neutral. Структура: pipeline, что качать, где считать, как организовать код.

***
""")

st.header("0. Общий каркас бэктеста")

st.markdown("""
1. **Выбор фреймворка**
    - Для простых/быстрых экспериментов: `pandas + numpy + numba` или `vectorbt` (особенно для cross-sectional).
    - Для реалистичного исполнения (маржа, ликвидации, частичные fill'ы): `backtrader` или свой event loop.
2. **Шаги пайплайна одинаковые для обеих стратегий:**

3) Сбор и очистка данных
4) Конструирование фич (funding, фактор, beta, basis и т.п.)
5) Правила стратегии (entry/exit, sizing, hedging)
6) Симуляция сделок с комиссиями/slippage/margin
7) PnL и риск-метрики
8) Robustness: walk-forward, режимы рынка, чувствительность к костам

***
""")

st.header("1. Funding Rate Arbitrage — Пошаговый гайд")

st.subheader("1.1. Данные: что и где брать")

st.markdown("""
Минимально по каждой бирже/инструменту:

- **Spot:**
    - OHLCV (1m/5m/15m)
    - Taker fees, maker fees (фикс из fee schedule биржи)
- **Perp:**
    - OHLCV
    - Funding rate + время начисления (timestamp версии «payment time»)
    - Maintenance margin, initial margin (из спецификации контракта)
- **Дополнительно** (по возможности):
    - Bid/ask или хотя бы mid price вокруг funding timestamps
    - Borrow rate (если берешь кредит под спот)

**Источники:**

- Биржевые API напрямую (через `ccxt`)
- CoinGlass / др. агрегаторы для funding-history, если хочешь быстро и кросс-биржево

**Практика:**
Сделай отдельный модуль `data/`:
""")

st.code("""
data/
  binance_btcusdt_spot_1m.parquet
  binance_btcusdt_perp_1m.parquet
  binance_btcusdt_funding.csv
""", language="text")

st.markdown("И обертки:")

st.code("""
class BinanceData:
    def load_spot(self, symbol): ...
    def load_perp(self, symbol): ...
    def load_funding(self, symbol): ...
""", language="python")

st.markdown("***")

st.subheader("1.2. Подготовка таймлайна funding")

st.markdown("""
Тебе нужен **единый таймлайн**, на котором:

- Есть цены spot и perp (частая частота, напр. 1m/5m)
- Отмечены **моменты funding-платежей** и величина funding за интервал

**Подход:**
""")

st.code("""
# 1. Берешь минутные/5-минутные свечи spot/perp → resample до 1m/5m
# 2. Funding series (8h points) → forward fill до следующего события
# 3. В отдельной колонке флаг: is_funding_time = True ровно на том баре, когда реально происходит начисление
""", language="python")

st.markdown("***")

st.subheader("1.3. Модель портфеля и маржи")

st.markdown("Удобно сделать класс `Portfolio`:")

st.code("""
class FundingArbPortfolio:
    def __init__(self, capital, leverage, fee_spot, fee_perp, mmr):
        self.equity = capital
        self.positions = {...}  # qty_spot, qty_perp
        self.leverage = leverage
        self.mmr = mmr  # maintenance margin ratio
        ...

    def open_delta_neutral(self, notional, spot_price, perp_price):
        # long spot, short perp
        # вычитаешь комиссии и кэшлок
        ...

    def close_all(self, spot_price, perp_price):
        # реализация PnL + закрытие
        ...

    def update_mark_to_market(self, spot_price, perp_price):
        # пересчет equity с учетом unrealized
        ...

    def apply_funding(self, notional, funding_rate, side):
        # side = 'short' / 'long' по perp
        ...

    def check_liquidation(self, perp_entry_price, perp_price, notional):
        # считает margin ratio и флаг ликвидации
        ...
""", language="python")

st.markdown("""
**Важно:**

- Отдельно хранить: `equity`, `margin_used` (на perp), `spot_value`, `unrealized_pnl_perp`
- Ликвидация как event: при `margin_ratio < maintenance_margin` → закрываешь позицию по худшей цене (можно добавить 1–2% extra slippage на ликвидацию).
""")

st.markdown("***")

st.subheader("1.4. Логика стратегии (entry / hold / exit)")

st.markdown("""
**Базовый вариант funding arb:**

1. В каждый момент **перед началом funding-интервала**: смотри `funding_rate_8h` (или annualized). Если `funding_rate > threshold` (напр. 0.01% за 8h, что ~11% годовых) → открываешь delta-neutral позицию с заданным notional.
2. Поддерживаешь позицию: не трогаешь до достижения basis stop-loss, смены знака funding (или падения ниже порога), события ликвидации/почти-ликвидации (margin_warning), наступления края риск-лимитов.
3. В момент funding: `apply_funding()` на текущий notional.
4. **Basis risk:** отслеживаешь `basis = P_perp - P_spot`. Если `|basis| > basis_threshold` (например, 3–5%) → фиксируешь PnL и закрываешь.

**Псевдокод цикла:**
""")

st.code("""
for t, row in data.iterrows():
    spot_price = row['spot']
    perp_price = row['perp']

    # 1) update MTM
    portfolio.update_mark_to_market(spot_price, perp_price)

    # 2) liquidation check
    if portfolio.check_liquidation(...):
        portfolio.force_liquidate(perp_price)
        continue

    # 3) strategy logic
    if not portfolio.has_position():
        if row['funding_8h'] > funding_threshold:
            portfolio.open_delta_neutral(target_notional, spot_price, perp_price)
    else:
        basis = perp_price - spot_price

        if abs(basis) > basis_sl_threshold:
            portfolio.close_all(spot_price, perp_price)
        elif row['funding_8h'] < min_funding_to_stay:
            portfolio.close_all(spot_price, perp_price)

    # 4) funding event
    if row['is_funding_time'] and portfolio.has_position():
        portfolio.apply_funding(current_notional, row['funding_8h'], side='short')

    log_equity[t] = portfolio.equity
""", language="python")

st.markdown("***")

st.subheader("1.5. Комиссии и slippage")

st.markdown("""
- **Комиссии:** `fee_spot`, `fee_perp` из fee schedule биржи; в backtest просто умножать notional на fee.
- **Slippage:** базовая модель: `slippage = base * (1 + k * volatility)`; либо таблица по размерам ордера (до 100k notional по BTC: 0.02–0.05%, при стрессах ×2–3).

**Применение:**
""")

st.code("fill_price = price * (1 + slippage * side_sign)  # side_sign = +1 для покупки", language="python")

st.markdown("***")

st.subheader("1.6. Анализ результатов")

st.markdown("""
По готовой equity curve:

- **PnL decomposition:** funding PnL vs basis PnL vs commissions
- **Risk:** Max DD, volatility, recovery time; частота/глубина basis-events
- **Regime analysis:** разбить по периодам bull / bear / high vol / low vol (по BTC)

Плюс: walk-forward по параметрам (`funding_threshold`, `basis_sl`, `leverage`, `position_size`); sensitivity — умножаешь все комиссии/slippage на 0.5x / 1x / 2x и смотришь, когда стратегия «умирает».

***
""")

st.header("2. Market Neutral Alt Strategy — Пошаговый гайд")

st.markdown("""
Эта стратегия больше про cross-section, поэтому удобнее: либо `pandas` + vectorization (особенно с `vectorbt`), либо свой event loop, если много деталей по исполнению.
""")

st.subheader("2.1. Данные и universe")

st.markdown("""
На каждый день/бар (обычно дневка или 4h): цена OHLCV по всем алтам; BTC-USD (спот или perp) — для beta и hedge; funding rates по perp'ам, если short через perp; маркеткап, ADV — для фильтров ликвидности; список delisted/делистингов.

**Пайплайн:**
""")

st.code("""
# 1) Собираешь все исторические пары, включая те, что уже умерли.
# 2) Фильтруешь по: age > 6 мес, avg_daily_volume > X, market_cap > Y
# 3) Запоминаешь даты, когда пара исчезает (delisting_date).
""", language="python")

st.markdown("На каждый день строишь **universe_t**.")

st.markdown("***")

st.subheader("2.2. Фактор (пример: 30-дневный momentum)")

st.code("""
# prices: DataFrame (index = date, columns = coins)
ret = prices.pct_change()

mom = prices / prices.shift(30) - 1   # простой 30d return
# Можно делать cross-sectional z-score:
mom_z = (mom - mom.mean(axis=1).values[:,None]) / mom.std(axis=1).values[:,None]
""", language="python")

st.markdown("**Ранжирование:**")

st.code("""
def build_long_short_buckets(mom_z_t, universe_t, q=0.2):
    s = mom_z_t[universe_t].dropna()
    n = len(s)
    if n < 10:
        return [], []
    s_sorted = s.sort_values()
    k = int(n * q)
    shorts = s_sorted.index[:k]
    longs  = s_sorted.index[-k:]
    return longs, shorts
""", language="python")

st.markdown("***")

st.subheader("2.3. Оценка beta и BTC hedge")

st.markdown("Rolling OLS к BTC:")

st.code("""
import statsmodels.api as sm

def rolling_beta(series, benchmark, window=60):
    betas = []
    for i in range(len(series)):
        if i < window:
            betas.append(np.nan)
            continue
        y = series.iloc[i-window:i]
        x = benchmark.iloc[i-window:i]
        X = sm.add_constant(x)
        model = sm.OLS(y, X).fit()
        betas.append(model.params[1])
    return pd.Series(betas, index=series.index)

betas = {}
for coin in prices.columns:
    betas[coin] = rolling_beta(ret[coin], ret['BTC'], window=90)
""", language="python")

st.markdown("""
На день t: `beta_L`, `beta_S`, `net_beta = beta_L - beta_S`; notional hedge в BTC: `btc_hedge_notional = net_beta * portfolio_value`. Можно фиксировать долю long/short (Long notional = 0.5 * equity, Short notional = 0.5 * equity) и отдельно добавлять BTC hedge сверху.
""")

st.markdown("***")

st.subheader("2.4. Конструкция портфеля и ребаланс")

st.markdown("""
**Ребаланс раз в N дней** (напр. 1 раз в 7 или 30 дней): на ребаланс-день определяешь longs/shorts из фактора, равный вес внутри корзин, считаешь beta корзин → размер BTC hedge; считаешь delta между текущими и целевыми весами; если drift маленький — не трогаешь.
""")

st.code("""
for t in dates:
    universe_t = universe[t]
    if is_rebalance_day(t):
        longs, shorts = build_long_short_buckets(mom_z.loc[t], universe_t)
        target_weights = build_target_weights(longs, shorts)

        # beta hedge
        beta_L = sum(target_weights[i] * betas[i].loc[t] for i in longs)
        beta_S = sum(target_weights[j] * betas[j].loc[t] for j in shorts)
        net_beta = beta_L - beta_S
        btc_hedge_weight = -net_beta  # short BTC если net_beta>0

        target_weights['BTC'] = btc_hedge_weight

        rebalance_portfolio(target_weights, prices.loc[t], fee, slippage_model)

    portfolio.update_mark_to_market(prices.loc[t])
    apply_funding_costs_for_shorts(...)
    log_equity[t] = portfolio.equity
""", language="python")

st.markdown("***")

st.subheader("2.5. Комиссии, funding, borrow")

st.markdown("""
- **Комиссии:** на каждое изменение позиции: `|Δnotional| * fee`.
- **Short через perp:** funding cost — ежедневно/каждый интервал списываешь `short_notional * funding_rate` (критично для альтов).
- **Short через spot borrow:** моделируешь borrow rate, плюс ограничения по размеру borrow.

Реалистично отдельно логировать: `PnL_price`, `PnL_funding`, `PnL_commissions`, `PnL_borrow`.
""")

st.markdown("***")

st.subheader("2.6. Режимный и robust-анализ")

st.markdown("""
1. **Regime split:** классифицируешь ежедневно (Bull vs Bear по 60-дневному return BTC, High vs Low vol по rolling std BTC). Считаешь Sharpe/Sortino по каждому режиму, Max DD, hit rate. Если Sharpe сильно > в bull и около 0/отрицательный в bear — это disguised beta.
2. **Walk-forward параметров:** внутри каждого train-window оптимизируешь lookback, quantile long/short, horizon rebalancing; тестируешь на OOS-окне.
""")

st.markdown("***")

st.header("3. Как это всё собрать в проект")

st.markdown("Предлагаемый layout:")

st.code("""
project/
  data/
  src/
    data_loader.py
    funding_arb/
      backtest.py
      portfolio.py
      config.yaml
    alt_market_neutral/
      factors.py
      portfolio.py
      backtest.py
    utils/
      slippage.py
      fees.py
      risk_metrics.py
  notebooks/
    01_explore_data.ipynb
    02_funding_arb_prototype.ipynb
    03_alt_mn_prototype.ipynb
  reports/
    funding_arb_report.html
    alt_mn_report.html
""", language="text")

st.markdown("В `notebooks/` — прототипирование; в `src/` — продакшн-код с конфигами; в `reports/` — автогенерация отчётов (quantstats или свой HTML).")

st.markdown("***")

st.header("4. На что особенно смотреть в результатах")

st.subheader("Funding Rate Arb")

st.markdown("""
- Декомпозиция доходности: % от funding vs % от basis
- Tail events: что с портфелем в FTX-моменты / март 2020 / май 2021
- Leverage sensitivity: как быстро DD растёт при увеличении плеча
- Cost sensitivity: при ×1.5–2 комиссий/slippage стратегия всё ещё жива?
""")

st.subheader("Alt Market-Neutral")

st.markdown("""
- **Ex-post beta** к BTC: OLS портфельных ретернов на BTC → beta должна быть ближе к 0.
- Cross-sectional robustness: меняется ли композиция names или одни и те же «фавориты» (crowding).
- Turnover: годовой turnover и сколько % годовой доходности съедают транзакционные издержки.
- Regime stability: режимы, где стратегия проваливается → нужно ли включать regime filter.
""")

st.markdown("---")
st.markdown("""
**Sources**

- [Binance: Get Funding Rate History](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History)
- [CoinGlass API](https://www.coinglass.com/CryptoApi)
""")
