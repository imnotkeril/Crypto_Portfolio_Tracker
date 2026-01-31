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
    
    # Get current portfolio
    portfolio = get_current_portfolio()
    transactions = get_transactions()
    
    # Current prices
    btc_price = get_current_price("BTC/USDT")
    eth_price = get_current_price("ETH/USDT")
    
    # Portfolio value
    portfolio_value = (
        portfolio['BTC'] * (btc_price or 0) +
        portfolio['ETH'] * (eth_price or 0) +
        portfolio['USDT']
    )
    
    # Display portfolio
    st.subheader("Current Portfolio")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("BTC", f"{portfolio['BTC']:.3f}", f"${btc_price:,.2f}" if btc_price else "")
        if btc_price:
            st.metric("BTC Value", f"${portfolio['BTC'] * btc_price:,.2f}")
    
    with col2:
        st.metric("ETH", f"{portfolio['ETH']:.3f}", f"${eth_price:,.2f}" if eth_price else "")
        if eth_price:
            st.metric("ETH Value", f"${portfolio['ETH'] * eth_price:,.2f}")
    
    with col3:
        st.metric("USDT", f"{portfolio['USDT']:,.2f}")
    
    with col4:
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
