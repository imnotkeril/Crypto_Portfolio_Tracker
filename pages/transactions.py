"""
Transactions page - transaction input and management
"""
import streamlit as st
import pandas as pd
from datetime import datetime, date
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.database import init_database, add_transaction, get_transactions, delete_transaction, get_current_portfolio
from utils.price_fetcher import get_price, get_current_price, find_dates_by_price
from utils.assets import get_available_assets


st.set_page_config(page_title="Transactions", page_icon="📊", layout="wide")

# Initialize database
init_database()

st.title("📊 Transactions")
st.markdown("Input buys and sells with automatic price fetching")

# Get existing transactions
transactions_df = get_transactions()

# Create form for adding new transaction
with st.expander("➕ Add Transaction", expanded=len(transactions_df) == 0):
    # Date input mode selection
    date_input_mode = st.radio(
        "Date Input Mode",
        ["By Date", "By Target Price"],
        key="date_input_mode",
        help="Select 'By Target Price' to find dates when price was close to specified value"
    )
    
    col1, col2, col3 = st.columns(3)
    
    # Date input based on mode
    selected_date_str = None
    transaction_date = None
    
    available_assets = get_available_assets()
    if date_input_mode == "By Date":
        with col1:
            transaction_date = st.date_input("Transaction Date", value=date.today(), key="tx_date")
        selected_date_str = transaction_date.strftime('%Y-%m-%d')
        with col2:
            asset = st.selectbox("Asset", available_assets, key="tx_asset")
        with col3:
            transaction_type = st.selectbox("Type", ["buy", "sell"], key="tx_type")
    else:  # By Target Price
        crypto_only = [a for a in available_assets if a != "USDT"]
        with col2:
            asset = st.selectbox("Asset", crypto_only if crypto_only else available_assets, key="tx_asset")
        with col3:
            transaction_type = st.selectbox("Type", ["buy", "sell"], key="tx_type")
        
        with col1:
            target_price = st.number_input(
                "Target Price (USDT)",
                min_value=0.0,
                value=0.0,
                step=100.0,
                format="%.2f",
                key="target_price"
            )
        
        # Year and month selection
        col_year, col_month = st.columns(2)
        with col_year:
            search_year = st.number_input("Year", min_value=2020, max_value=2030, value=2022, key="search_year")
        with col_month:
            search_month = st.number_input("Month", min_value=1, max_value=12, value=5, key="search_month")
        
        # Find dates by price
        if target_price > 0 and asset != "USDT":
            if st.button("🔍 Find Matching Dates", key="find_dates_btn"):
                with st.spinner(f"Searching dates for {asset} at price {target_price:.2f} USDT..."):
                    matching_dates = find_dates_by_price(
                        asset, 
                        target_price, 
                        transaction_type, 
                        search_year, 
                        search_month
                    )
                    
                    if len(matching_dates) > 0:
                        st.session_state['matching_dates'] = matching_dates
                        st.session_state['saved_target_price'] = target_price
                        st.success(f"Found {len(matching_dates)} matching dates!")
                    else:
                        st.warning(f"No matching dates found for price {target_price:.2f} USDT in {search_month}/{search_year}")
                        st.session_state['matching_dates'] = None
            
            # Show matching dates if found
            if 'matching_dates' in st.session_state and st.session_state['matching_dates'] is not None:
                matching_dates = st.session_state['matching_dates']
                # Sort by date (ascending - earliest first)
                matching_dates = matching_dates.sort_values('date', ascending=True).reset_index(drop=True)
                
                st.subheader("📅 Matching Dates:")
                
                # Format for display
                display_dates = []
                for idx, row in matching_dates.iterrows():
                    match_info = ""
                    if row['match_type'] == 'exact':
                        match_info = "✅ Exact Match"
                    elif row['match_type'] == 'high_low':
                        match_info = "📊 Price was in day's range"
                    else:
                        match_info = "📈 Close Price"
                    
                    display_dates.append({
                        'Date': row['date'],
                        'Close Price': f"{row['close_price']:,.2f}",
                        'Min/Max': f"{row['low']:,.2f} / {row['high']:,.2f}",
                        'Deviation': f"{row['price_diff_pct']:.2f}%",
                        'Match Type': match_info
                    })
                
                display_df = pd.DataFrame(display_dates)
                st.dataframe(display_df, use_container_width=True, hide_index=True)
                
                # Date selection - sorted by date (earliest first)
                date_options = matching_dates['date'].tolist()
                date_labels = []
                for date_val in date_options:
                    row = matching_dates[matching_dates['date'] == date_val].iloc[0]
                    label = f"{date_val} (price: {row['close_price']:,.2f}, deviation: {row['price_diff_pct']:.2f}%)"
                    date_labels.append(label)
                
                selected_date_idx = st.selectbox(
                    "Select Transaction Date",
                    range(len(date_options)),
                    format_func=lambda x: date_labels[x],
                    key="selected_date_idx"
                )
                
                if selected_date_idx is not None:
                    selected_date_str = date_options[selected_date_idx]
                    transaction_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
                    st.info(f"✅ Selected date: {selected_date_str}")
        elif target_price == 0:
            st.info("Enter target price and click 'Find Matching Dates'")
    
    # If date is not selected yet (for price-based mode), don't show rest of form
    if date_input_mode == "By Target Price" and selected_date_str is None:
        st.stop()
    
    # Input method selection
    input_method = st.radio(
        "Input Method",
        ["Asset Quantity", "Position Percentage", "USDT Amount"],
        key="input_method"
    )
    
    # Get portfolio at date for percentage calculation
    from utils.database import get_portfolio_at_date
    date_str = selected_date_str if selected_date_str else transaction_date.strftime('%Y-%m-%d')
    portfolio_at_date = get_portfolio_at_date(date_str)
    
    quantity = 0.0
    value_usdt = 0.0
    
    if input_method == "Asset Quantity":
        quantity = st.number_input(
            f"{asset} Quantity",
            min_value=0.0,
            value=0.0,
            step=0.001,
            format="%.3f",
            key="tx_quantity"
        )
        if quantity > 0:
            # Get price to calculate value
            use_auto_price = st.checkbox("Automatically fetch price from Binance", value=True, key="auto_price")
            if not use_auto_price:
                manual_price = st.number_input("Price (USDT)", min_value=0.0, value=0.0, step=0.01, key="manual_price")
                if manual_price > 0:
                    value_usdt = quantity * manual_price
            else:
                price = get_price(asset, date_str)
                if price:
                    value_usdt = quantity * price
                    st.info(f"Price on {date_str}: {price:.2f} USDT")
    
    elif input_method == "Position Percentage":
        if asset == "USDT":
            st.warning("For USDT, use USDT amount input")
        else:
            current_qty = portfolio_at_date.get(asset, 0.0)
            if current_qty > 0:
                st.info(f"Current {asset} position on {date_str}: {current_qty:.3f}")
                percentage = st.number_input(
                    "Position Percentage (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=0.0,
                    step=0.1,
                    key="tx_percentage"
                )
                if percentage > 0:
                    quantity = current_qty * (percentage / 100)
                    st.info(f"Will {transaction_type}: {quantity:.3f} {asset}")
                    # Get price
                    use_auto_price = st.checkbox("Automatically fetch price from Binance", value=True, key="auto_price_pct")
                    if not use_auto_price:
                        manual_price = st.number_input("Price (USDT)", min_value=0.0, value=0.0, step=0.01, key="manual_price_pct")
                        if manual_price > 0:
                            value_usdt = quantity * manual_price
                    else:
                        price = get_price(asset, date_str)
                        if price:
                            value_usdt = quantity * price
                            st.info(f"Price on {date_str}: {price:.2f} USDT | Amount: {value_usdt:.2f} USDT")
            else:
                st.warning(f"On {date_str}, {asset} position is 0. Add a buy first.")
    
    elif input_method == "USDT Amount":
        value_usdt = st.number_input(
            "Amount (USDT)",
            min_value=0.0,
            value=0.0,
            step=0.01,
            key="tx_value_usdt"
        )
        if value_usdt > 0 and asset != "USDT":
            # Get price to calculate quantity
            use_auto_price = st.checkbox("Automatically fetch price from Binance", value=True, key="auto_price_usdt")
            if not use_auto_price:
                manual_price = st.number_input("Price (USDT)", min_value=0.0, value=0.0, step=0.01, key="manual_price_usdt")
                if manual_price > 0:
                    quantity = value_usdt / manual_price
            else:
                price = get_price(asset, date_str)
                if price:
                    quantity = value_usdt / price
                    st.info(f"Price on {date_str}: {price:.2f} USDT | Quantity: {quantity:.3f} {asset}")
        elif asset == "USDT":
            quantity = value_usdt
    
    # Final price input (if needed and not already calculated)
    manual_price_final = None
    if asset != "USDT":
        st.markdown("---")
        # For price-based mode, show option to use target price or close price
        if date_input_mode == "By Target Price" and 'saved_target_price' in st.session_state and st.session_state['saved_target_price'] > 0:
            use_target_price = st.checkbox(
                f"Use target price ({st.session_state['saved_target_price']:.2f} USDT)", 
                value=True, 
                key="use_target_price"
            )
            if not use_target_price:
                use_auto_price_final = st.checkbox("Use close price of selected date", value=True, key="auto_price_final")
                if not use_auto_price_final:
                    manual_price_final = st.number_input("Price (USDT) - manual", min_value=0.0, value=0.0, step=0.01, key="manual_price_final")
            else:
                use_auto_price_final = False
        else:
            use_auto_price_final = st.checkbox("Automatically fetch price from Binance", value=True, key="auto_price_final")
            if not use_auto_price_final:
                manual_price_final = st.number_input("Price (USDT) - manual", min_value=0.0, value=0.0, step=0.01, key="manual_price_final")
    
    if st.button("Add Transaction", type="primary"):
        try:
            # Use selected_date_str if available (from price-based mode), otherwise use transaction_date
            if selected_date_str:
                date_str = selected_date_str
            else:
                date_str = transaction_date.strftime('%Y-%m-%d')
            
            # Determine price
            price = None
            if asset != "USDT":
                # Get date_input_mode from session state if not available
                current_date_input_mode = st.session_state.get('date_input_mode', date_input_mode if 'date_input_mode' in locals() else "By Date")
                
                # If using price-based mode and target price is set, check user preference
                if current_date_input_mode == "By Target Price" and 'saved_target_price' in st.session_state and st.session_state['saved_target_price'] > 0:
                    if st.session_state.get('use_target_price', True):
                        # Use target price
                        price = st.session_state['saved_target_price']
                        st.info(f"Using target price: {price:.2f} USDT")
                    else:
                        # Check if use_auto_price_final is set
                        use_auto_price_final = st.session_state.get('auto_price_final', True)
                        if use_auto_price_final:
                            # Use close price of selected date
                            price = get_price(asset, date_str)
                            if price is None:
                                st.error(f"Failed to get price for {asset} on {date_str}. Disable automatic fetching and enter price manually.")
                                st.stop()
                            st.info(f"Using close price: {price:.2f} USDT")
                        elif manual_price_final and manual_price_final > 0:
                            price = manual_price_final
                        else:
                            st.error("Specify price. Choose to use target price, close price, or enter price manually.")
                            st.stop()
                else:
                    use_auto_price_final = st.session_state.get('auto_price_final', True)
                    if use_auto_price_final:
                        price = get_price(asset, date_str)
                        if price is None:
                            st.error(f"Failed to get price for {asset} on {date_str}. Disable automatic fetching and enter price manually.")
                            st.stop()
                    elif manual_price_final and manual_price_final > 0:
                        price = manual_price_final
                    else:
                        # Try to get price from previous inputs
                        price = st.session_state.get('manual_price') or st.session_state.get('manual_price_pct') or st.session_state.get('manual_price_usdt')
                        if not price or price <= 0:
                            st.error("Specify price. Disable automatic fetching and enter price manually.")
                            st.stop()
            else:
                price = 1.0
            
            # Calculate final quantity and value based on input method
            final_quantity = 0.0
            final_value = 0.0
            
            if input_method == "Asset Quantity":
                if quantity <= 0:
                    st.error("Specify quantity")
                    st.stop()
                final_quantity = quantity
                final_value = final_quantity * price
                
            elif input_method == "Position Percentage":
                current_qty = portfolio_at_date.get(asset, 0.0)
                if current_qty <= 0:
                    st.error(f"On {date_str}, {asset} position is 0. Add a buy first.")
                    st.stop()
                percentage = st.session_state.get('tx_percentage', 0.0)
                if percentage <= 0:
                    st.error("Specify position percentage")
                    st.stop()
                final_quantity = current_qty * (percentage / 100)
                final_value = final_quantity * price
                
            elif input_method == "USDT Amount":
                if value_usdt <= 0:
                    st.error("Specify USDT amount")
                    st.stop()
                if asset == "USDT":
                    final_quantity = value_usdt
                    final_value = value_usdt
                else:
                    final_quantity = value_usdt / price
                    final_value = value_usdt
            
            if final_quantity <= 0:
                st.error("Quantity must be greater than 0. Check entered data.")
                st.stop()
            
            # Add transaction
            add_transaction(date_str, asset, transaction_type, final_quantity, price, final_value)
            
            st.success(f"✅ Transaction added: {transaction_type.upper()} {final_quantity:.3f} {asset} at price {price:.2f} USDT (amount: {final_value:.2f} USDT)")
            st.rerun()
            
        except Exception as e:
            st.error(f"Error adding transaction: {e}")
            st.exception(e)

# Display current portfolio
st.subheader("Current Portfolio")
portfolio = get_current_portfolio()

cols = st.columns(min(4, len(portfolio)) or 1)
for i, (asset, qty) in enumerate(sorted(portfolio.items(), key=lambda x: (0 if x[0] == 'USDT' else 1, x[0]))):
    with cols[i % 4]:
        if asset == 'USDT':
            st.metric(asset, f"{qty:,.2f}")
        else:
            st.metric(asset, f"{qty:.4f}")

if len(transactions_df) > 0:
    portfolio_value = portfolio.get('USDT', 0.0)
    for asset in portfolio:
        if asset != 'USDT':
            p = get_current_price(f"{asset}/USDT")
            if p:
                portfolio_value += portfolio[asset] * p
    st.metric("Portfolio Value", f"{portfolio_value:,.2f} USDT")

# Display transactions
if len(transactions_df) > 0:
    st.subheader("Transaction History")
    
    # Sort transactions: by date (ascending - oldest first), then by price within same day
    # For buy: higher prices first (if price drops, higher limit orders execute first)
    # For sell: lower prices first (if price rises, lower limit orders execute first)
    transactions_sorted = transactions_df.copy()
    
    # Create a helper column for sorting: price with sign based on transaction type
    # For buy: negative price (so higher prices sort first when ascending)
    # For sell: positive price (so lower prices sort first when ascending)
    transactions_sorted['_sort_price'] = transactions_sorted.apply(
        lambda row: -row['price'] if row['type'] == 'buy' else row['price'],
        axis=1
    )
    
    # Sort by date (ascending), then by sort_price (ascending)
    transactions_sorted = transactions_sorted.sort_values(['date', '_sort_price'], ascending=[True, True])
    
    # Format display
    display_df = transactions_sorted[['date', 'asset', 'type', 'quantity', 'price', 'value']].copy()
    # Format quantity column before renaming
    display_df['quantity'] = display_df.apply(
        lambda row: f"{row['quantity']:.3f}" if row['asset'] != 'USDT' else f"{row['quantity']:.2f}",
        axis=1
    )
    display_df.columns = ['Date', 'Asset', 'Type', 'Quantity', 'Price (USDT)', 'Value (USDT)']
    display_df['Type'] = display_df['Type'].str.upper()
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # Summary by asset
    st.subheader("Summary by Asset")
    assets_in_txs = sorted(transactions_df['asset'].unique())
    summary_data = []
    for asset in assets_in_txs:
        asset_txs = transactions_df[transactions_df['asset'] == asset]
        if len(asset_txs) > 0:
            buy_txs = asset_txs[asset_txs['type'] == 'buy']
            sell_txs = asset_txs[asset_txs['type'] == 'sell']
            
            buy_qty = buy_txs['quantity'].sum()
            sell_qty = sell_txs['quantity'].sum()
            net_qty = buy_qty - sell_qty
            
            buy_value = buy_txs['value'].sum()
            sell_value = sell_txs['value'].sum()
            
            avg_buy_price = buy_txs['price'].mean() if len(buy_txs) > 0 else 0
            avg_sell_price = sell_txs['price'].mean() if len(sell_txs) > 0 else 0
            
            summary_data.append({
                'Asset': asset,
                'Bought': f"{buy_qty:.3f}" if asset != 'USDT' else f"{buy_qty:,.2f}",
                'Sold': f"{sell_qty:.3f}" if asset != 'USDT' else f"{sell_qty:,.2f}",
                'Net Quantity': f"{net_qty:.3f}" if asset != 'USDT' else f"{net_qty:,.2f}",
                'Spent (USDT)': f"{buy_value:,.2f}",
                'Received (USDT)': f"{sell_value:,.2f}",
                'Avg Buy Price': f"{avg_buy_price:,.2f}" if avg_buy_price > 0 else "-",
                'Avg Sell Price': f"{avg_sell_price:,.2f}" if avg_sell_price > 0 else "-"
            })
    
    if summary_data:
        summary_df = pd.DataFrame(summary_data)
        st.dataframe(summary_df, use_container_width=True, hide_index=True)
    else:
        st.info("No data for summary")
    
    # Delete transaction
    st.subheader("Delete Transactions")
    if len(transactions_df) > 0:
        # Sort by date descending (latest first)
        transactions_sorted = transactions_df.sort_values('date', ascending=False)
        delete_options = []
        for _, row in transactions_sorted.iterrows():
            qty = row['quantity']
            qty_str = f"{qty:.3f}" if row['asset'] != 'USDT' else f"{qty:.2f}"
            label = f"{row['date']} | {row['type'].upper()} {qty_str} {row['asset']} @ {row['price']:.2f} USDT"
            delete_options.append((row['id'], label))
        
        selected_delete = st.selectbox(
            "Select transaction to delete",
            options=delete_options,
            format_func=lambda x: x[1] if isinstance(x, tuple) else x
        )
        
        if st.button("🗑️ Delete Transaction", type="primary"):
            if selected_delete:
                record_id = selected_delete[0] if isinstance(selected_delete, tuple) else selected_delete
                delete_transaction(record_id)
                st.success("Transaction deleted")
                st.rerun()
else:
    st.info("No transactions. Add your first transaction above.")
