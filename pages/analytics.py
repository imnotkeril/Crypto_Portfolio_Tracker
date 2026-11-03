"""
Analytics page - portfolio metrics and charts
"""
import json
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.database import init_database, get_transactions
from utils.portfolio_calculator import calculate_portfolio_history
from utils.metrics import calculate_all_metrics
from utils.price_fetcher import get_price_range


st.set_page_config(page_title="Analytics", page_icon="📈", layout="wide")

# Initialize database
init_database()

st.title("📈 Portfolio Analytics")
st.markdown("Performance metrics and charts")

# Calculate portfolio history
with st.spinner("Calculating portfolio history..."):
    portfolio_history = calculate_portfolio_history()

if len(portfolio_history) == 0:
    st.warning("No data for analysis. Add transactions on the 'Transactions' page.")
    st.stop()

# Calculate metrics
portfolio_values = portfolio_history['total_value']
metrics = calculate_all_metrics(portfolio_values)

# Helper function to format metrics safely
def safe_format(value, format_str="{:.2f}", default="0.00"):
    """Format value safely, handling nan/inf"""
    if value is None or (isinstance(value, (int, float)) and (np.isnan(value) or np.isinf(value))):
        return default
    try:
        return format_str.format(value)
    except:
        return default

# Display key metrics
st.subheader("Key Metrics")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Return", f"{safe_format(metrics['total_return'], '{:.2f}')}%")
    st.metric("Average Annual", f"{safe_format(metrics['avg_yearly_return'], '{:.2f}')}%")

with col2:
    st.metric("Average Monthly", f"{safe_format(metrics['avg_monthly_return'], '{:.2f}')}%")
    st.metric("Volatility", f"{safe_format(metrics['volatility'], '{:.2f}')}%")

with col3:
    st.metric("Max Drawdown", f"{safe_format(metrics['max_drawdown'], '{:.2f}')}%")
    st.metric("Average Drawdown", f"{safe_format(metrics['avg_drawdown'], '{:.2f}')}%")

with col4:
    sharpe_val = safe_format(metrics['sharpe_ratio'], '{:.2f}')
    st.metric("Sharpe Ratio", sharpe_val if sharpe_val != "0.00" else "N/A")
    sortino_val = safe_format(metrics['sortino_ratio'], '{:.2f}')
    st.metric("Sortino Ratio", sortino_val if sortino_val != "0.00" else "N/A")

st.markdown("---")

# Monthly and Yearly Returns Heatmap
st.subheader("📅 Returns by Month and Year")

col_heat1, col_heat2 = st.columns(2)

with col_heat1:
    st.write("**Monthly Returns**")
    monthly_returns = metrics['monthly_returns']
    if len(monthly_returns) > 0:
        # Create heatmap data - include all months from 1 to 12
        monthly_df = pd.DataFrame({
            'date': pd.to_datetime(monthly_returns.index),
            'return': monthly_returns.values
        })
        monthly_df['year'] = monthly_df['date'].dt.year
        monthly_df['month'] = monthly_df['date'].dt.month
        
        # Get all years and months
        all_years = sorted(monthly_df['year'].unique())
        all_months = list(range(1, 13))
        
        # Create complete pivot table with all months
        heatmap_data = monthly_df.pivot_table(
            values='return',
            index='year',
            columns='month',
            aggfunc='first'
        )
        
        # Reindex to include all months
        heatmap_data = heatmap_data.reindex(columns=all_months)
        heatmap_data = heatmap_data.reindex(index=all_years)
        
        # Create heatmap
        fig_monthly = px.imshow(
            heatmap_data,
            labels=dict(x="Month", y="Year", color="Return (%)"),
            x=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
            color_continuous_scale='RdYlGn',
            aspect="auto",
            text_auto=".1f"
        )
        fig_monthly.update_layout(height=400)
        st.plotly_chart(fig_monthly, use_container_width=True)
    else:
        st.info("No monthly returns data")

with col_heat2:
    st.write("**Yearly Returns**")
    yearly_returns = metrics['yearly_returns']
    if len(yearly_returns) > 0:
        # Create bar chart for yearly returns
        yearly_df = pd.DataFrame({
            'Year': yearly_returns.index.strftime('%Y'),
            'Return (%)': yearly_returns.values
        })
        
        # Color bars based on positive/negative
        colors = ['#2ca02c' if x >= 0 else '#d62728' for x in yearly_df['Return (%)']]
        
        # Calculate max absolute value for better y-axis range
        max_abs = max(abs(yearly_df['Return (%)'].min()), abs(yearly_df['Return (%)'].max()))
        y_range = [-max_abs * 1.2, max_abs * 1.2]
        
        fig_yearly = go.Figure()
        fig_yearly.add_trace(go.Bar(
            x=yearly_df['Year'],
            y=yearly_df['Return (%)'],
            marker_color=colors,
            text=yearly_df['Return (%)'].apply(lambda x: f"{x:.2f}%"),
            textposition='auto',  # Auto position to avoid clipping
            textfont=dict(size=12, color='white')
        ))
        fig_yearly.update_layout(
            title='Yearly Returns',
            xaxis_title='Year',
            yaxis_title='Return (%)',
            height=400,
            showlegend=False,
            yaxis=dict(range=y_range)  # Set range to show all values
        )
        st.plotly_chart(fig_yearly, use_container_width=True)
    else:
        st.info("No yearly returns data")

st.markdown("---")

# Charts section
st.subheader("📊 Charts")

# Cumulative returns and Drawdowns in subplots
st.write("**Cumulative Returns and Drawdowns**")

# Calculate drawdowns
portfolio_values_sorted = portfolio_values.sort_index()
running_max = portfolio_values_sorted.expanding().max()
drawdowns = ((portfolio_values_sorted - running_max) / running_max) * 100

# Create subplots
fig_combined = make_subplots(
    rows=2, cols=1,
    subplot_titles=('Portfolio Cumulative Returns', 'Portfolio Drawdowns'),
    vertical_spacing=0.15,
    row_heights=[0.6, 0.4]
)

# Cumulative returns - ensure we have data
cumulative_returns = metrics['cumulative_returns']
if len(cumulative_returns) > 0 and not cumulative_returns.isna().all():
    # Filter out NaN values
    cum_ret_clean = cumulative_returns.dropna()
    if len(cum_ret_clean) > 0:
        fig_combined.add_trace(
            go.Scatter(
                x=cum_ret_clean.index,
                y=cum_ret_clean.values,
                mode='lines',
                name='Cumulative Returns',
                line=dict(color='#2ca02c', width=2),
                fill='tozeroy',
                fillcolor='rgba(44, 160, 44, 0.2)'
            ),
            row=1, col=1
        )
    else:
        # If no valid data, show zero line
        fig_combined.add_trace(
            go.Scatter(
                x=portfolio_values_sorted.index,
                y=[0] * len(portfolio_values_sorted),
                mode='lines',
                name='Cumulative Returns',
                line=dict(color='#2ca02c', width=2)
            ),
            row=1, col=1
        )
else:
    # If no cumulative returns data, calculate it manually
    initial_value = portfolio_values_sorted.iloc[0]
    if initial_value > 0:
        cum_ret_manual = ((portfolio_values_sorted - initial_value) / initial_value) * 100
        fig_combined.add_trace(
            go.Scatter(
                x=cum_ret_manual.index,
                y=cum_ret_manual.values,
                mode='lines',
                name='Cumulative Returns',
                line=dict(color='#2ca02c', width=2),
                fill='tozeroy',
                fillcolor='rgba(44, 160, 44, 0.2)'
            ),
            row=1, col=1
        )

# Drawdowns
if len(drawdowns) > 0:
    fig_combined.add_trace(
        go.Scatter(
            x=drawdowns.index,
            y=drawdowns.values,
            mode='lines',
                name='Drawdown',
            line=dict(color='#d62728', width=2),
            fill='tozeroy',
            fillcolor='rgba(214, 39, 40, 0.3)'
        ),
        row=2, col=1
    )

fig_combined.update_xaxes(title_text="Date", row=2, col=1)
fig_combined.update_yaxes(title_text="Return (%)", row=1, col=1)
fig_combined.update_yaxes(title_text="Drawdown (%)", row=2, col=1)
fig_combined.update_layout(
    height=700,
    hovermode='x unified',
    showlegend=False
)

st.plotly_chart(fig_combined, use_container_width=True)

# Portfolio value over time
st.write("**Portfolio Value Over Time**")
fig_portfolio = go.Figure()
fig_portfolio.add_trace(go.Scatter(
    x=portfolio_history.index,
    y=portfolio_history['total_value'],
    mode='lines',
    name='Total Value',
    line=dict(color='#1f77b4', width=2),
    fill='tozeroy',
    fillcolor='rgba(31, 119, 180, 0.2)'
))
fig_portfolio.update_layout(
    title='Portfolio Value Over Time',
    xaxis_title='Date',
    yaxis_title='Value (USDT)',
    hovermode='x unified',
    height=400
)
st.plotly_chart(fig_portfolio, use_container_width=True)

# Asset price chart with buy/sell markers
st.write("**Asset Chart with Entry/Exit Points**")
transactions = get_transactions()
assets_with_txs = sorted(transactions['asset'].unique()) if len(transactions) > 0 else []
# Only crypto assets (exclude USDT for price chart)
chart_assets = [a for a in assets_with_txs if a != 'USDT']
asset_selection = st.selectbox("Select Asset", chart_assets if chart_assets else ["BTC", "ETH"])

if asset_selection:
    asset_transactions = transactions[transactions['asset'] == asset_selection]
    
    if len(asset_transactions) > 0:
        # Get price range
        start_date = asset_transactions['date'].min()
        end_date = asset_transactions['date'].max()
        
        price_data = get_price_range(f"{asset_selection}/USDT", start_date, end_date)
        
        if len(price_data) > 0:
            fig_asset = make_subplots(specs=[[{"secondary_y": False}]])
            
            # Price line
            fig_asset.add_trace(go.Scatter(
                x=price_data['date'],
                y=price_data['price'],
                mode='lines',
                name=f'{asset_selection} цена',
                line=dict(color='#1f77b4', width=1)
            ))
            
            # Buy markers
            buy_txs = asset_transactions[asset_transactions['type'] == 'buy']
            if len(buy_txs) > 0:
                fig_asset.add_trace(go.Scatter(
                    x=buy_txs['date'],
                    y=buy_txs['price'],
                    mode='markers',
                    name='Buy',
                    marker=dict(
                        symbol='triangle-up',
                        size=10,
                        color='green',
                        line=dict(width=1, color='darkgreen')
                    )
                ))
            
            # Sell markers
            sell_txs = asset_transactions[asset_transactions['type'] == 'sell']
            if len(sell_txs) > 0:
                fig_asset.add_trace(go.Scatter(
                    x=sell_txs['date'],
                    y=sell_txs['price'],
                    mode='markers',
                    name='Sell',
                    marker=dict(
                        symbol='triangle-down',
                        size=10,
                        color='red',
                        line=dict(width=1, color='darkred')
                    )
                ))
            
            fig_asset.update_layout(
                title=f'{asset_selection} Chart with Transaction Markers',
                xaxis_title='Date',
                yaxis_title='Price (USDT)',
                hovermode='x unified',
                height=500
            )
            
            st.plotly_chart(fig_asset, use_container_width=True)
        else:
            st.info(f"Failed to get price data for {asset_selection}")
    else:
        st.info(f"No transactions for {asset_selection}")

# Portfolio composition
st.write("**Portfolio Composition**")
fig_composition = go.Figure()

if len(portfolio_history) > 0:
    latest = portfolio_history.iloc[-1]
    if 'assets_value' in portfolio_history.columns:
        try:
            av = json.loads(latest['assets_value']) if isinstance(latest['assets_value'], str) else latest['assets_value']
        except Exception:
            av = {
                'BTC': latest.get('BTC_value', 0),
                'ETH': latest.get('ETH_value', 0),
                'USDT': latest.get('USDT_value', 0),
            }
    else:
        av = {
            'BTC': latest.get('BTC_value', 0),
            'ETH': latest.get('ETH_value', 0),
            'USDT': latest.get('USDT_value', 0),
        }
    av = {k: v for k, v in av.items() if v and float(v) > 0}
    if av:
        assets = list(av.keys())
        values = [float(av[a]) for a in assets]
        colors = ['#f7931a', '#627eea', '#26a17b', '#f0b90b', '#00d4aa', '#5ac8fa', '#ff6b6b'][:len(assets)]
        fig_composition.add_trace(go.Bar(
            x=assets,
            y=values,
            name='Value',
            marker_color=colors[:len(assets)]
        ))
        fig_composition.update_layout(
            title='Current Portfolio Composition',
            xaxis_title='Asset',
            yaxis_title='Value (USDT)',
            height=400
        )
        st.plotly_chart(fig_composition, use_container_width=True)
        fig_pie = go.Figure(data=[go.Pie(
            labels=assets,
            values=values,
            hole=0.3,
            marker_colors=colors[:len(assets)]
        )])
        fig_pie.update_layout(title='Portfolio Distribution', height=400)
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("No portfolio value data for composition.")

# Funding and Pool Income Section - moved to bottom
st.markdown("---")
st.subheader("💰 Funding and Pool Income")

# Check if funding_income and pool_income columns exist
has_funding_data = 'funding_income' in portfolio_history.columns
has_pool_data = 'pool_income' in portfolio_history.columns

if has_funding_data or has_pool_data:
    # Prepare data for monthly aggregation
    portfolio_history_reset = portfolio_history.reset_index()
    portfolio_history_reset['year_month'] = pd.to_datetime(portfolio_history_reset['date']).dt.to_period('M')
    
    # Group by month and take max (income is same for all days in month, but we want one value per month)
    monthly_income = portfolio_history_reset.groupby('year_month').agg({
        'funding_income': 'max' if has_funding_data else 'first',
        'pool_income': 'max' if has_pool_data else 'first'
    }).reset_index()
    
    # Calculate total income (sum of monthly incomes)
    total_funding = monthly_income['funding_income'].sum() if has_funding_data else 0.0
    total_pool = monthly_income['pool_income'].sum() if has_pool_data else 0.0
    total_passive_income = total_funding + total_pool
    
    # Display metrics
    col_fund1, col_fund2, col_fund3 = st.columns(3)
    
    with col_fund1:
        st.metric("💰 Funding Income", f"${total_funding:,.2f}")
    
    with col_fund2:
        st.metric("🏊 Pool Income", f"${total_pool:,.2f}")
    
    with col_fund3:
        st.metric("📊 Total Passive Income", f"${total_passive_income:,.2f}")
    
    # Calculate percentage of total portfolio value
    if len(portfolio_history) > 0:
        latest_value = portfolio_history['total_value'].iloc[-1]
        if latest_value > 0:
            funding_pct = (total_funding / latest_value) * 100
            pool_pct = (total_pool / latest_value) * 100
            total_pct = (total_passive_income / latest_value) * 100
            
            st.caption(f"💡 Passive income represents {total_pct:.2f}% of current portfolio value "
                      f"({funding_pct:.2f}% funding, {pool_pct:.2f}% pools)")
    
    st.markdown("---")
    
    # Monthly income chart
    st.write("**Monthly Income Dynamics**")
    
    monthly_income['year_month_str'] = monthly_income['year_month'].astype(str)
    
    # Create chart
    fig_income = go.Figure()
    
    if has_funding_data:
        fig_income.add_trace(go.Bar(
            x=monthly_income['year_month_str'],
            y=monthly_income['funding_income'],
            name='Funding Income',
            marker_color='#f7931a',
            text=monthly_income['funding_income'].apply(lambda x: f"${x:,.0f}" if x > 0 else ""),
            textposition='outside'
        ))
    
    if has_pool_data:
        fig_income.add_trace(go.Bar(
            x=monthly_income['year_month_str'],
            y=monthly_income['pool_income'],
            name='Pool Income',
            marker_color='#26a17b',
            text=monthly_income['pool_income'].apply(lambda x: f"${x:,.0f}" if x > 0 else ""),
            textposition='outside'
        ))
    
    fig_income.update_layout(
        title='Monthly Funding and Pool Income',
        xaxis_title='Period',
        yaxis_title='Income (USDT)',
        barmode='stack',
        height=400,
        hovermode='x unified'
    )
    
    st.plotly_chart(fig_income, use_container_width=True)
    
    # Cumulative income chart
    st.write("**Cumulative Funding and Pool Income**")
    
    # Calculate cumulative income from monthly data
    monthly_income_sorted = monthly_income.sort_values('year_month')
    cumulative_funding = monthly_income_sorted['funding_income'].cumsum() if has_funding_data else pd.Series()
    cumulative_pool = monthly_income_sorted['pool_income'].cumsum() if has_pool_data else pd.Series()
    
    fig_cumulative = go.Figure()
    
    if has_funding_data and len(cumulative_funding) > 0:
        fig_cumulative.add_trace(go.Scatter(
            x=monthly_income_sorted['year_month_str'],
            y=cumulative_funding.values,
            mode='lines+markers',
            name='Cumulative Funding Income',
            line=dict(color='#f7931a', width=2),
            fill='tozeroy',
            fillcolor='rgba(247, 147, 26, 0.2)'
        ))
    
    if has_pool_data and len(cumulative_pool) > 0:
        fig_cumulative.add_trace(go.Scatter(
            x=monthly_income_sorted['year_month_str'],
            y=cumulative_pool.values,
            mode='lines+markers',
            name='Cumulative Pool Income',
            line=dict(color='#26a17b', width=2),
            fill='tozeroy',
            fillcolor='rgba(38, 161, 123, 0.2)'
        ))
    
    if has_funding_data and has_pool_data and len(cumulative_funding) > 0 and len(cumulative_pool) > 0:
        total_cumulative = cumulative_funding + cumulative_pool
        fig_cumulative.add_trace(go.Scatter(
            x=monthly_income_sorted['year_month_str'],
            y=total_cumulative.values,
            mode='lines+markers',
            name='Total Cumulative Income',
            line=dict(color='#1f77b4', width=3, dash='dash')
        ))
    
    fig_cumulative.update_layout(
        title='Cumulative Funding and Pool Income',
        xaxis_title='Period',
        yaxis_title='Cumulative Income (USDT)',
        hovermode='x unified',
        height=400
    )
    
    st.plotly_chart(fig_cumulative, use_container_width=True)
    
    # Monthly income table
    st.write("**Monthly Income Breakdown**")
    
    monthly_detailed = monthly_income.copy()
    monthly_detailed['total_income'] = monthly_detailed['funding_income'] + monthly_detailed['pool_income']
    monthly_detailed = monthly_detailed[monthly_detailed['total_income'] > 0]  # Only show months with income
    
    if len(monthly_detailed) > 0:
        display_table = monthly_detailed.copy()
        display_table['Period'] = display_table['year_month'].astype(str)
        display_table['Funding (USDT)'] = display_table['funding_income'].apply(lambda x: f"{x:,.2f}")
        display_table['Pools (USDT)'] = display_table['pool_income'].apply(lambda x: f"{x:,.2f}")
        display_table['Total (USDT)'] = display_table['total_income'].apply(lambda x: f"{x:,.2f}")
        
        display_table = display_table[['Period', 'Funding (USDT)', 'Pools (USDT)', 'Total (USDT)']]
        st.dataframe(display_table, use_container_width=True, hide_index=True)
    else:
        st.info("No income data for selected period")
else:
    st.info("💡 Add funding and pool data on the respective pages to see their contribution to portfolio returns.")
