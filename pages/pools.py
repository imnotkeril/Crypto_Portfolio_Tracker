"""
USDT Pools page - track USDT pools by month
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.database import init_database, add_pool_rate, get_pool_rates, delete_pool_rate


st.set_page_config(page_title="USDT Pools", page_icon="🏊", layout="wide")

# Initialize database
init_database()

st.title("🏊 USDT Pools")
st.markdown("Track USDT pools by month with APY. Amount is calculated automatically based on sales.")

# Auto-populate button with average historical APY
if st.button("🔄 Auto-populate average APY (2022-2025)", type="secondary"):
    with st.spinner("Populating data..."):
        # Average APY for USDT pools (approximate historical values)
        pool_apy = {
            2022: 8.0,  # Higher rates in 2022
            2023: 6.5,  # Moderate rates
            2024: 5.0,  # Lower rates
            2025: 4.5,  # Current rates
        }
        
        count = 0
        from datetime import datetime as dt
        
        for year in range(2022, 2026):
            for month in range(1, 13):
                if year == 2025 and month > dt.now().month:
                    break
                
                apy = pool_apy.get(year, 5.0)
                try:
                    add_pool_rate(year, month, apy)
                    count += 1
                except Exception as e:
                    st.warning(f"Error adding {year}-{month:02d}: {e}")
        
        st.success(f"✅ Added {count} pool records for period 2022-2025!")
        st.rerun()

# Get existing pool rates
pools_df = get_pool_rates()

# Create form for adding new pool rate
with st.expander("➕ Add Pool", expanded=len(pools_df) == 0):
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        year = st.number_input("Year", min_value=2022, max_value=2030, value=datetime.now().year, key="pool_year")
    
    with col2:
        month = st.number_input("Month", min_value=1, max_value=12, value=datetime.now().month, key="pool_month")
    
    with col3:
        apy = st.number_input("APY (%)", min_value=0.0, value=0.0, step=0.01, key="pool_apy",
                             help="Annual percentage yield of the pool. Amount is calculated automatically based on real USDT in pool")
    
    if st.button("Add Pool"):
        if apy > 0:
            add_pool_rate(year, month, apy)
            st.success(f"Pool added: {year}-{month:02d} - APY {apy}%")
            st.rerun()
        else:
            st.error("Specify APY")

# Display existing pool rates
if len(pools_df) > 0:
    st.subheader("Pool History")
    
    # Format display
    display_df = pools_df.copy()
    display_df = display_df[['year', 'month', 'apy']]
    display_df.columns = ['Year', 'Month', 'APY (%)']
    display_df['Period'] = display_df['Year'].astype(str) + '-' + display_df['Month'].astype(str).str.zfill(2)
    display_df = display_df[['Period', 'APY (%)']]
    st.caption("💡 Pool amount and income are calculated automatically based on real USDT from sales")
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # Summary statistics
    st.subheader("Summary Statistics")
    col1, col2 = st.columns(2)
    
    with col1:
        avg_apy = display_df['APY (%)'].mean()
        st.metric("Average APY", f"{avg_apy:.2f}%")
    
    with col2:
        min_apy = display_df['APY (%)'].min()
        max_apy = display_df['APY (%)'].max()
        st.metric("APY Range", f"{min_apy:.2f}% - {max_apy:.2f}%")
    
    # Summary by year
    st.subheader("Summary by Year")
    yearly_summary = pools_df.groupby('year').agg({
        'apy': 'mean'
    }).reset_index()
    yearly_summary.columns = ['Year', 'Average APY (%)']
    
    st.dataframe(yearly_summary, use_container_width=True, hide_index=True)
    
    # Chart
    st.subheader("APY Chart")
    chart_df = display_df.copy()
    chart_df['Period'] = pd.to_datetime(chart_df['Period'])
    chart_df = chart_df.sort_values('Period')
    
    import plotly.express as px
    fig = px.line(chart_df, x='Period', y='APY (%)', 
                  title='USDT Pool APY Dynamics',
                  markers=True)
    fig.update_layout(xaxis_title="Period", yaxis_title="APY (%)")
    st.plotly_chart(fig, use_container_width=True)
    
    # Delete option
    st.subheader("Delete Records")
    if len(pools_df) > 0:
        delete_options = []
        for _, row in pools_df.iterrows():
            label = f"{row['year']}-{row['month']:02d} | {row['apy']:.2f}% APY"
            delete_options.append((row['id'], label))
        
        selected_delete = st.selectbox(
            "Select record to delete",
            options=delete_options,
            format_func=lambda x: x[1] if isinstance(x, tuple) else x
        )
        
        if st.button("🗑️ Delete", type="primary"):
            if selected_delete:
                record_id = selected_delete[0] if isinstance(selected_delete, tuple) else selected_delete
                delete_pool_rate(record_id)
                st.success("Record deleted")
                st.rerun()
    
else:
    st.info("No pool records. Add your first record above.")
