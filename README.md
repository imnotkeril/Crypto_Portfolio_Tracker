# Crypto Portfolio Tracker

A comprehensive cryptocurrency portfolio tracking application with automatic metric calculation and visualization.

## Features

- **Transaction Tracking**: Record buy/sell transactions with automatic price fetching from Binance
- **Coin-M Funding**: Track Coin-M funding income for BTC and ETH positions
- **USDT Pools**: Track USDT pool yields with automatic return calculation
- **Performance Metrics**: Calculate returns, volatility, Sharpe ratio, Sortino ratio, and drawdowns
- **Visualizations**: Interactive charts for cumulative returns, entry/exit points, and portfolio composition
- **Price Discovery**: Find historical dates when prices matched your target (useful for reconstructing transaction history)

## Installation

Install all dependencies:

```bash
pip install -r requirements.txt
```

Or install manually:

```bash
pip install streamlit pandas numpy plotly ccxt python-dateutil requests statsmodels
```

**Important:** If you're using a virtual environment, make sure it's activated before installing dependencies and running the application.

## Running the Application

Run the application with:

```bash
streamlit run main.py
```

Or via Python:

```bash
python -m streamlit run main.py
```

If you encounter `ModuleNotFoundError: No module named 'ccxt'`, ensure that:
1. Dependencies are installed in the same Python environment as Streamlit
2. You're using the correct Python interpreter
3. Virtual environment is activated (if used)

## Project Structure

```
Crypto_portfolio/
├── main.py                 # Main dashboard page
├── pages/                  # Application pages
│   ├── transactions.py     # Transaction management
│   ├── funding.py         # Coin-M funding tracking
│   ├── pools.py           # USDT pool tracking
│   ├── analytics.py       # Performance analytics
│   ├── backtest.py        # Funding-arb / alt market-neutral backtests
│   └── guide.py           # Backtest guide (static text)
├── utils/                  # Utility modules
│   ├── database.py        # SQLite database operations
│   ├── price_fetcher.py   # Price fetching from Binance API
│   ├── assets.py          # Binance USDT asset list (cached)
│   ├── backtest_data.py   # Backtest data loaders (Binance or synthetic)
│   ├── backtest_funding_arb.py  # Funding-arb strategy
│   ├── backtest_alt_mn.py       # Alt market-neutral strategy
│   ├── portfolio_calculator.py  # Portfolio value calculation
│   └── metrics.py         # Performance metrics calculation
├── scripts/                # Helper scripts
│   ├── auto_populate_funding.py  # Auto-populate funding data
│   ├── populate_funding_data.py  # Populate funding from API
│   └── migrate_database.py      # Database migration
├── data/                   # Data directory
│   ├── portfolio.db       # SQLite database
│   └── cache/             # Price cache
└── requirements.txt       # Python dependencies
```

## Usage

1. **Transactions**: Add all your buy and sell transactions on the "Transactions" page
   - Supports multiple input methods: asset quantity, position percentage, or USDT amount
   - Automatic price fetching from Binance
   - Price discovery feature to find dates when prices matched your target

2. **Funding**: Enter Coin-M funding rates on the "Funding" page
   - Funding amounts are calculated automatically based on your actual positions
   - Supports auto-population with historical averages

3. **Pools**: Enter USDT pool APY data on the "Pools" page
   - Pool amounts and income are calculated automatically based on sales
   - Supports auto-population with historical averages

4. **Analytics**: View performance metrics and charts on the "Analytics" page
   - Key metrics: total return, annual return, volatility, Sharpe ratio, Sortino ratio
   - Interactive charts: cumulative returns, drawdowns, portfolio composition
   - Monthly and yearly return heatmaps

## Database

The application uses SQLite database stored in `data/portfolio.db`. The database is automatically created on first run.

### Tables

- `transactions`: Buy/sell transactions
- `funding_rates`: Coin-M funding rates (percentage only, amounts calculated automatically)
- `pool_rates`: USDT pool APY rates (amounts calculated automatically)
- `portfolio_snapshots`: Historical portfolio snapshots for metrics

## Price Data

Price data is fetched from Binance API via the `ccxt` library. Historical prices are cached locally in `data/cache/price_cache.json` to reduce API calls.

## Requirements

- Python 3.8+
- streamlit >= 1.28.0
- pandas >= 2.0.0
- numpy >= 1.24.0
- plotly >= 5.17.0
- ccxt >= 4.0.0
- python-dateutil >= 2.8.2
- requests >= 2.28.0
- statsmodels >= 0.14.0

## License

This project is open source and available for personal use.

## Notes

- The application automatically calculates funding amounts based on your actual portfolio positions
- Pool amounts are automatically calculated based on sales (USDT from sales goes into pools)
- All income calculations are done monthly based on average positions/balances
- Price data requires internet connection to fetch from Binance API
