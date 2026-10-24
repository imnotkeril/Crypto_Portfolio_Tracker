"""
Main page - portfolio tracker dashboard
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(__file__))
from utils.database import init_database, get_current_portfolio, get_transactions
from utils.price_fetcher import get_current_price
from utils.portfolio_calculator import calculate_portfolio_history


st.set_page_config(
    page_title="Crypto Portfolio",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database
init_database()

# Sidebar navigation
st.sidebar.title("💰 Crypto Portfolio")
st.sidebar.markdown("---")
st.sidebar.markdown("**Main Page**")
st.sidebar.markdown("---")
st.sidebar.markdown("Use the menu on the left to navigate between pages")

# Main content
if True:  # Always show dashboard on main page
    st.title("📊 Portfolio Dashboard")
    
    portfolio = get_current_portfolio()
    transactions = get_transactions()

    # Build list of crypto assets (exclude USDT for price fetch)
    crypto_assets = [a for a in portfolio.keys() if a != 'USDT']
    prices = {}
    for asset in crypto_assets:
        prices[asset] = get_current_price(f"{asset}/USDT")

    portfolio_value = portfolio.get('USDT', 0.0)
    for asset in crypto_assets:
        qty = portfolio.get(asset, 0.0)
        p = prices.get(asset)
        if p:
            portfolio_value += qty * p

    st.subheader("Current Portfolio")

    # Show metrics: up to 4 per row, then new row
    cols_per_row = 4
    assets_sorted = sorted(portfolio.keys(), key=lambda a: (0 if a == 'USDT' else 1, a))
    for i in range(0, len(assets_sorted), cols_per_row):
        row_assets = assets_sorted[i : i + cols_per_row]
        cols = st.columns(len(row_assets))
        for col, asset in zip(cols, row_assets):
            with col:
                qty = portfolio[asset]
                if asset == 'USDT':
                    st.metric(asset, f"{qty:,.2f}")
                else:
                    price = prices.get(asset)
                    price_str = f"${price:,.2f}" if price else "—"
                    st.metric(asset, f"{qty:.4f}", price_str)
                    if price and qty > 0:
                        st.metric(f"{asset} Value", f"${qty * price:,.2f}")

    st.metric("Total Value", f"${portfolio_value:,.2f}")
    
    # Quick stats
    if len(transactions) > 0:
        st.subheader("Quick Statistics")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_txs = len(transactions)
            st.metric("Total Transactions", total_txs)
        
        with col2:
            buy_txs = len(transactions[transactions['type'] == 'buy'])
            st.metric("Buys", buy_txs)
        
        with col3:
            sell_txs = len(transactions[transactions['type'] == 'sell'])
            st.metric("Sells", sell_txs)
        
        # Recent transactions
        st.subheader("Recent Transactions")
        recent_txs = transactions.tail(5).sort_values('date', ascending=False)
        if len(recent_txs) > 0:
            display_recent = recent_txs[['date', 'asset', 'type', 'quantity', 'price']].copy()
            display_recent.columns = ['Date', 'Asset', 'Type', 'Quantity', 'Price']
            display_recent['Type'] = display_recent['Type'].str.upper()
            st.dataframe(display_recent, use_container_width=True, hide_index=True)
    
    # Portfolio history chart (if available)
    try:
        portfolio_history = calculate_portfolio_history()
        if len(portfolio_history) > 0:
            st.subheader("Portfolio Value History")
            
            import plotly.graph_objects as go
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=portfolio_history.index,
                y=portfolio_history['total_value'],
                mode='lines',
                name='Portfolio Value',
                line=dict(color='#2ca02c', width=2),
                fill='tozeroy'
            ))
            fig.update_layout(
                title='Portfolio Value Over Time',
                xaxis_title='Date',
                yaxis_title='Value (USDT)',
                hovermode='x unified',
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.info("Chart will be available after adding transactions")
    
    # Instructions
    st.markdown("---")
    st.subheader("How to Use")
    st.markdown("""
    1. **Transactions**: Add all your buys and sells on the "Transactions" page
    2. **Funding**: Enter Coin-M funding income on the "Funding" page
    3. **Pools**: Enter USDT pool data on the "Pools" page
    4. **Analytics**: View metrics and charts on the "Analytics" page
    """)

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("**Version:** 1.0.0")
st.sidebar.markdown("**Period:** from 2022")
