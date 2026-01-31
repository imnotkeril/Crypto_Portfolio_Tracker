"""
Funding rates page - Coin-M funding for BTC and ETH
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.database import init_database, add_funding_rate, get_funding_rates, delete_funding_rate


st.set_page_config(page_title="Coin-M Funding", page_icon="💰", layout="wide")

# Initialize database
init_database()

st.title("💰 Coin-M Funding")
st.markdown("Track Coin-M funding for BTC and ETH by month")

# Auto-populate button with average historical rates
if st.button("🔄 Auto-populate average values (2022-2025)", type="secondary"):
    with st.spinner("Populating data..."):
        # Average annual funding rates based on historical data
        # These are approximate averages - user can adjust manually
        funding_rates = {
            2022: {'BTC': 7.5, 'ETH': 8.0},  # Higher rates in 2022
            2023: {'BTC': 6.5, 'ETH': 7.0},  # Moderate rates
            2024: {'BTC': 5.5, 'ETH': 6.0},  # Lower rates
            2025: {'BTC': 5.0, 'ETH': 5.5},  # Current rates
        }
        
        count = 0
        from datetime import datetime as dt
        
        for year in range(2022, 2026):
            for month in range(1, 13):
                if year == 2025 and month > dt.now().month:
                    break
                
                for asset in ['BTC', 'ETH']:
                    annual_rate = funding_rates.get(year, {}).get(asset, 6.0)
                    try:
                        add_funding_rate(year, month, asset, annual_rate)
                        count += 1
                    except Exception as e:
                        st.warning(f"Error adding {year}-{month:02d} {asset}: {e}")
        
        st.success(f"✅ Added {count} funding records for period 2022-2025!")
        st.rerun()

# Get existing funding rates
funding_df = get_funding_rates()

# Create form for adding new funding rate
with st.expander("➕ Add Funding", expanded=len(funding_df) == 0):
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        year = st.number_input("Year", min_value=2022, max_value=2030, value=datetime.now().year, key="funding_year")
    
    with col2:
        month = st.number_input("Month", min_value=1, max_value=12, value=datetime.now().month, key="funding_month")
    
    with col3:
        asset = st.selectbox("Asset", ["BTC", "ETH"], key="funding_asset")
    
    with col4:
        percentage = st.number_input("Funding Percentage (%)", min_value=0.0, value=0.0, step=0.01, key="funding_percentage", 
                                     help="Annual funding rate. Amount is calculated automatically based on real positions")
    
    if st.button("Add Funding"):
        if percentage > 0:
            add_funding_rate(year, month, asset, percentage)
            st.success(f"Funding added: {asset} for {year}-{month:02d} - {percentage}% annual")
            st.rerun()
        else:
            st.error("Specify funding percentage")

# Display existing funding rates
if len(funding_df) > 0:
    st.subheader("Funding History")
    
    # Format display
    display_df = funding_df.copy()
    display_df = display_df[['year', 'month', 'asset', 'percentage']]
    display_df.columns = ['Year', 'Month', 'Asset', 'Percentage (%)']
    display_df['Period'] = display_df['Year'].astype(str) + '-' + display_df['Month'].astype(str).str.zfill(2)
    display_df = display_df[['Period', 'Asset', 'Percentage (%)']]
    st.caption("💡 Funding amount is calculated automatically based on real positions in portfolio")
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # Summary by asset
    st.subheader("Summary by Asset")
    summary = funding_df.groupby('asset').agg({
        'percentage': 'mean'
    }).reset_index()
    summary.columns = ['Asset', 'Average Percentage (%)']
    st.dataframe(summary, use_container_width=True, hide_index=True)
    
    # Summary by year
    st.subheader("Summary by Year")
    yearly_summary = funding_df.groupby(['year', 'asset']).agg({
        'percentage': 'mean'
    }).reset_index()
    yearly_summary.columns = ['Year', 'Asset', 'Average Percentage (%)']
    yearly_pivot = yearly_summary.pivot(index='Year', columns='Asset', values='Average Percentage (%)').fillna(0)
    st.dataframe(yearly_pivot, use_container_width=True)
    
    # Delete option
    st.subheader("Delete Records")
    if len(funding_df) > 0:
        delete_options = []
        for _, row in funding_df.iterrows():
            label = f"{row['year']}-{row['month']:02d} | {row['asset']} | {row['percentage']:.2f}%"
            delete_options.append((row['id'], label))
        
        selected_delete = st.selectbox(
            "Select record to delete",
            options=delete_options,
            format_func=lambda x: x[1] if isinstance(x, tuple) else x
        )
        
        if st.button("🗑️ Delete", type="primary"):
            if selected_delete:
                record_id = selected_delete[0] if isinstance(selected_delete, tuple) else selected_delete
                delete_funding_rate(record_id)
                st.success("Record deleted")
                st.rerun()
else:
    st.info("No funding records. Add your first record above.")
