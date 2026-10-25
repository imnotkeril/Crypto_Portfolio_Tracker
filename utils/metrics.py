"""
Metrics calculation module
Calculates portfolio performance metrics: returns, volatility, Sharpe, Sortino, drawdowns
"""
import pandas as pd
import numpy as np
from typing import Dict, Tuple


def calculate_returns(portfolio_values: pd.Series) -> pd.Series:
    """
    Calculate period returns
    Args:
        portfolio_values: Series with portfolio values over time
    Returns:
        Series with returns
    """
    return portfolio_values.pct_change().fillna(0)


def calculate_total_return(initial_value: float, current_value: float) -> float:
    """Calculate total return percentage"""
    if initial_value == 0 or initial_value is None or np.isnan(initial_value):
        return 0.0
    if current_value is None or np.isnan(current_value):
        return 0.0
    return ((current_value - initial_value) / initial_value) * 100


def calculate_annual_return(portfolio_values: pd.Series) -> float:
    """
    Calculate annualized return
    Args:
        portfolio_values: Series with portfolio values over time
    Returns:
        Annualized return as percentage
    """
    if len(portfolio_values) < 2:
        return 0.0
    
    # Find first non-zero value
    non_zero_mask = (portfolio_values != 0) & (~portfolio_values.isna())
    if non_zero_mask.any():
        first_non_zero_idx = portfolio_values[non_zero_mask].index[0]
        initial_value = portfolio_values.loc[first_non_zero_idx]
    else:
        initial_value = portfolio_values.iloc[0]
    
    if initial_value == 0 or initial_value is None or np.isnan(initial_value):
        return 0.0
    
    total_return = (portfolio_values.iloc[-1] / initial_value) - 1
    
    # Calculate number of years
    dates = pd.to_datetime(portfolio_values.index)
    # DatetimeIndex supports direct indexing, not iloc
    days_diff = (dates[-1] - dates[0]).days
    if days_diff <= 0:
        return 0.0
    
    years = days_diff / 365.25
    if years == 0:
        return 0.0
    
    if total_return <= -1:
        return -100.0
    
    try:
        annual_return = ((1 + total_return) ** (1 / years)) - 1
        if not np.isfinite(annual_return):
            return 0.0
        return annual_return * 100
    except:
        return 0.0


def calculate_monthly_returns(portfolio_values: pd.Series) -> pd.Series:
    """
    Calculate monthly returns
    Args:
        portfolio_values: Series with portfolio values indexed by date
    Returns:
        Series with monthly returns
    """
    portfolio_df = pd.DataFrame({'value': portfolio_values})
    portfolio_df.index = pd.to_datetime(portfolio_df.index)
    monthly = portfolio_df.resample('ME').last()
    
    # Filter out zero values before calculating returns
    monthly_non_zero = monthly[monthly['value'] > 0]
    
    if len(monthly_non_zero) < 2:
        return pd.Series([], dtype=float)
    
    monthly_returns = monthly_non_zero['value'].pct_change().dropna() * 100
    return monthly_returns


def calculate_avg_monthly_return(monthly_returns: pd.Series) -> float:
    """
    Calculate average monthly return
    Args:
        monthly_returns: Series with monthly returns
    Returns:
        Average monthly return as percentage
    """
    if len(monthly_returns) == 0:
        return 0.0
    
    # Filter out infinite and NaN values
    monthly_returns_clean = monthly_returns.replace([np.inf, -np.inf], np.nan).dropna()
    
    if len(monthly_returns_clean) == 0:
        return 0.0
    
    avg = monthly_returns_clean.mean()
    if not np.isfinite(avg):
        return 0.0
    return avg


def calculate_avg_yearly_return(yearly_returns: pd.Series) -> float:
    """
    Calculate average yearly return
    Args:
        yearly_returns: Series with yearly returns
    Returns:
        Average yearly return as percentage
    """
    if len(yearly_returns) == 0:
        return 0.0
    avg = yearly_returns.mean()
    if not np.isfinite(avg):
        return 0.0
    return avg


def calculate_yearly_returns(portfolio_values: pd.Series) -> pd.Series:
    """
    Calculate yearly returns
    Args:
        portfolio_values: Series with portfolio values indexed by date
    Returns:
        Series with yearly returns
    """
    portfolio_df = pd.DataFrame({'value': portfolio_values})
    portfolio_df.index = pd.to_datetime(portfolio_df.index)
    yearly = portfolio_df.resample('YE').last()
    yearly_returns = yearly['value'].pct_change().fillna(0) * 100
    return yearly_returns


def calculate_volatility(returns: pd.Series, annualized: bool = True) -> float:
    """
    Calculate volatility (standard deviation of returns)
    Args:
        returns: Series with returns
        annualized: If True, annualize the volatility
    Returns:
        Volatility as percentage
    """
    if len(returns) < 2:
        return 0.0
    
    # Filter out NaN and infinite values
    returns_clean = returns.replace([np.inf, -np.inf], np.nan).dropna()
    if len(returns_clean) < 2:
        return 0.0
    
    # Assuming daily returns
    std = returns_clean.std()
    if not np.isfinite(std):
        return 0.0
    
    if annualized:
        # Annualize: multiply by sqrt(252) for daily data
        std = std * np.sqrt(252)
    
    result = std * 100
    if not np.isfinite(result):
        return 0.0
    return result


def calculate_max_drawdown(portfolio_values: pd.Series) -> Tuple[float, str, str]:
    """
    Calculate maximum drawdown
    Args:
        portfolio_values: Series with portfolio values
    Returns:
        Tuple of (max_drawdown_percentage, peak_date, trough_date)
    """
    if len(portfolio_values) < 2:
        return (0.0, "", "")
    
    # Calculate running maximum (peak)
    running_max = portfolio_values.expanding().max()
    
    # Calculate drawdown
    drawdown = (portfolio_values - running_max) / running_max * 100
    
    # Find maximum drawdown
    max_dd = drawdown.min()
    trough_idx = drawdown.idxmin()
    
    # Find the peak before the trough
    peak_value = running_max.loc[trough_idx]
    peak_idx = portfolio_values[portfolio_values == peak_value].index[0]
    
    return (abs(max_dd), str(peak_idx), str(trough_idx))


def calculate_avg_drawdown(portfolio_values: pd.Series) -> float:
    """
    Calculate average drawdown
    Args:
        portfolio_values: Series with portfolio values
    Returns:
        Average drawdown as percentage
    """
    if len(portfolio_values) < 2:
        return 0.0
    
    running_max = portfolio_values.expanding().max()
    drawdown = (portfolio_values - running_max) / running_max * 100
    
    # Only consider negative drawdowns
    negative_dd = drawdown[drawdown < 0]
    
    if len(negative_dd) == 0:
        return 0.0
    
    return abs(negative_dd.mean())


def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.0) -> float:
    """
    Calculate Sharpe ratio
    Args:
        returns: Series with returns
        risk_free_rate: Annual risk-free rate (default 0)
    Returns:
        Sharpe ratio
    """
    if len(returns) < 2:
        return 0.0
    
    # Filter out NaN and infinite values
    returns_clean = returns.replace([np.inf, -np.inf], np.nan).dropna()
    if len(returns_clean) < 2:
        return 0.0
    
    # Annualize returns and risk-free rate
    mean_return = returns_clean.mean() * 252  # Assuming daily returns
    std_return = returns_clean.std() * np.sqrt(252)
    
    if std_return == 0 or not np.isfinite(std_return):
        return 0.0
    
    sharpe = (mean_return - risk_free_rate / 100) / std_return
    if not np.isfinite(sharpe):
        return 0.0
    return sharpe


def calculate_sortino_ratio(returns: pd.Series, risk_free_rate: float = 0.0) -> float:
    """
    Calculate Sortino ratio (only downside deviation)
    Args:
        returns: Series with returns
        risk_free_rate: Annual risk-free rate (default 0)
    Returns:
        Sortino ratio
    """
    if len(returns) < 2:
        return 0.0
    
    # Filter out NaN and infinite values
    returns_clean = returns.replace([np.inf, -np.inf], np.nan).dropna()
    if len(returns_clean) < 2:
        return 0.0
    
    # Annualize returns
    mean_return = returns_clean.mean() * 252  # Assuming daily returns
    
    # Calculate downside deviation (only negative returns)
    downside_returns = returns_clean[returns_clean < 0]
    if len(downside_returns) == 0:
        # If no downside, return high value but finite
        if mean_return > 0:
            return 999.0  # High but finite value
        return 0.0
    else:
        downside_std = downside_returns.std() * np.sqrt(252)
    
    if downside_std == 0 or not np.isfinite(downside_std):
        if mean_return > 0:
            return 999.0
        return 0.0
    
    sortino = (mean_return - risk_free_rate / 100) / downside_std
    if not np.isfinite(sortino):
        return 0.0
    return sortino


def calculate_cumulative_returns(portfolio_values: pd.Series) -> pd.Series:
    """
    Calculate cumulative returns
    Args:
        portfolio_values: Series with portfolio values
    Returns:
        Series with cumulative returns as percentage
    """
    if len(portfolio_values) < 2:
        return pd.Series([0.0], index=portfolio_values.index)
    
    # Find first non-zero value as initial value
    non_zero_mask = (portfolio_values != 0) & (~portfolio_values.isna())
    if not non_zero_mask.any():
        # All values are zero or NaN
        return pd.Series([0.0] * len(portfolio_values), index=portfolio_values.index)
    
    first_non_zero_idx = portfolio_values[non_zero_mask].index[0]
    initial_value = portfolio_values.loc[first_non_zero_idx]
    
    if initial_value == 0 or initial_value is None or np.isnan(initial_value):
        return pd.Series([0.0] * len(portfolio_values), index=portfolio_values.index)
    
    cumulative = ((portfolio_values - initial_value) / initial_value) * 100
    return cumulative


def calculate_all_metrics(portfolio_values: pd.Series, risk_free_rate: float = 0.0) -> Dict:
    """
    Calculate all portfolio metrics
    Args:
        portfolio_values: Series with portfolio values indexed by date
        risk_free_rate: Annual risk-free rate
    Returns:
        Dictionary with all metrics
    """
    portfolio_values = portfolio_values.sort_index()
    returns = calculate_returns(portfolio_values)
    
    # Find first non-zero value for total return calculation
    non_zero_mask = (portfolio_values != 0) & (~portfolio_values.isna())
    if non_zero_mask.any():
        first_non_zero_idx = portfolio_values[non_zero_mask].index[0]
        initial_value = portfolio_values.loc[first_non_zero_idx]
    else:
        initial_value = portfolio_values.iloc[0]
    
    final_value = portfolio_values.iloc[-1]
    total_return = calculate_total_return(initial_value, final_value)
    annual_return = calculate_annual_return(portfolio_values)
    monthly_returns = calculate_monthly_returns(portfolio_values)
    yearly_returns = calculate_yearly_returns(portfolio_values)
    avg_monthly_return = calculate_avg_monthly_return(monthly_returns)
    avg_yearly_return = calculate_avg_yearly_return(yearly_returns)
    
    volatility = calculate_volatility(returns)
    max_dd, peak_date, trough_date = calculate_max_drawdown(portfolio_values)
    avg_dd = calculate_avg_drawdown(portfolio_values)
    sharpe = calculate_sharpe_ratio(returns, risk_free_rate)
    sortino = calculate_sortino_ratio(returns, risk_free_rate)
    cumulative_returns = calculate_cumulative_returns(portfolio_values)
    
    return {
        'total_return': total_return,
        'annual_return': annual_return,
        'avg_monthly_return': avg_monthly_return,
        'avg_yearly_return': avg_yearly_return,
        'monthly_returns': monthly_returns,
        'yearly_returns': yearly_returns,
        'volatility': volatility,
        'max_drawdown': max_dd,
        'max_drawdown_peak_date': peak_date,
        'max_drawdown_trough_date': trough_date,
        'avg_drawdown': avg_dd,
        'sharpe_ratio': sharpe,
        'sortino_ratio': sortino,
        'cumulative_returns': cumulative_returns,
        'returns': returns
    }
