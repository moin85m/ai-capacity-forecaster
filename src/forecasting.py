"""Capacity Forecasting Module.

Provides explainable linear trend forecasting and time-to-threshold estimation
for infrastructure capacity metrics (CPU, Memory, Network).
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd


@dataclass
class MetricForecast:
    """Forecast and trend summary for a single capacity metric."""
    metric_name: str
    display_name: str
    current_value: float
    recent_average: float
    slope_per_hour: float  # Percentage points per hour
    r_squared: float
    warning_threshold: float
    critical_threshold: float
    warning_breach_hours: Optional[float]
    critical_breach_hours: Optional[float]
    warning_eta_text: str
    critical_eta_text: str
    status: str  # "HEALTHY", "WARNING_BREACHED", "CRITICAL_BREACHED", "BREACH_IMMINENT", "TRENDING_UP", "STABLE"
    projection_explanation: str


def format_hours_to_human(hours: Optional[float]) -> str:
    """Format fractional hours into human readable 'Xh Ym' string."""
    if hours is None:
        return "No breach projected"
    if hours <= 0:
        return "Threshold already exceeded"
    
    total_minutes = int(round(hours * 60))
    h = total_minutes // 60
    m = total_minutes % 60
    
    if h == 0:
        return f"~{m}m"
    if m == 0:
        return f"~{h}h"
    return f"~{h}h {m}m"


def compute_linear_trend(values: np.ndarray, hours_interval: float = 1.0) -> Tuple[float, float]:
    """Compute linear regression slope (units/hr) and R-squared coefficient.
    
    Args:
        values: 1D array of metric values ordered chronologically.
        hours_interval: Time step between consecutive points in hours.
        
    Returns:
        (slope_per_hour, r_squared)
    """
    n = len(values)
    if n < 2:
        return 0.0, 0.0
    
    x = np.arange(n) * hours_interval
    y = values
    
    # Calculate slope and intercept using least squares
    x_mean = np.mean(x)
    y_mean = np.mean(y)
    
    ss_xx = np.sum((x - x_mean) ** 2)
    ss_yy = np.sum((y - y_mean) ** 2)
    ss_xy = np.sum((x - x_mean) * (y - y_mean))
    
    if ss_xx == 0:
        return 0.0, 0.0
    
    slope = ss_xy / ss_xx
    
    # R-squared
    if ss_yy > 0:
        r_squared = (ss_xy ** 2) / (ss_xx * ss_yy)
    else:
        r_squared = 1.0 if slope == 0 else 0.0
        
    return float(slope), float(r_squared)


def forecast_metric(
    df: pd.DataFrame,
    metric_col: str,
    display_name: str,
    lookback_points: int = 12,
    warning_threshold: float = 75.0,
    critical_threshold: float = 90.0,
) -> MetricForecast:
    """Calculate linear forecast and threshold breach estimates for a specific metric.
    
    Args:
        df: DataFrame containing the time series data (must include metric_col).
        metric_col: Column name in df (e.g. 'cpu_percent').
        display_name: Human readable label (e.g. 'CPU Utilization').
        lookback_points: Number of recent data points to use for trend calculation.
        warning_threshold: Percentage threshold for warning (default 75%).
        critical_threshold: Percentage threshold for critical (default 90%).
        
    Returns:
        MetricForecast dataclass instance.
    """
    if metric_col not in df.columns:
        raise ValueError(f"Column '{metric_col}' not found in dataframe.")
    
    series = df[metric_col].dropna().values
    if len(series) == 0:
        raise ValueError(f"No non-null data available for column '{metric_col}'.")
    
    current_val = float(series[-1])
    
    # Slice the recent lookback window
    window_data = series[-lookback_points:] if len(series) >= lookback_points else series
    recent_avg = float(np.mean(window_data))
    
    # Compute linear slope per hour
    slope, r2 = compute_linear_trend(window_data, hours_interval=1.0)
    
    # Status and breach projection
    warning_hours: Optional[float] = None
    critical_hours: Optional[float] = None
    
    # 1. Critical threshold evaluation
    if current_val >= critical_threshold:
        critical_hours = 0.0
        status = "CRITICAL_BREACHED"
    elif slope > 0.01:
        hours_needed = (critical_threshold - current_val) / slope
        critical_hours = max(0.0, hours_needed)
        status = "BREACH_IMMINENT" if critical_hours <= 2.0 else "TRENDING_UP"
    else:
        critical_hours = None
        status = "STABLE"

    # 2. Warning threshold evaluation
    if current_val >= warning_threshold:
        warning_hours = 0.0
        if status != "CRITICAL_BREACHED":
            status = "WARNING_BREACHED"
    elif slope > 0.01:
        hours_needed = (warning_threshold - current_val) / slope
        warning_hours = max(0.0, hours_needed)
        if status == "STABLE":
            status = "TRENDING_UP"
    else:
        warning_hours = None

    # Human-readable strings
    warning_eta_text = format_hours_to_human(warning_hours)
    critical_eta_text = format_hours_to_human(critical_hours)
    
    # Transparent explanation string
    if current_val >= critical_threshold:
        explanation = (
            f"Observed value ({current_val:.1f}%) has already exceeded the critical capacity limit "
            f"({critical_threshold:.1f}%). Immediate mitigation required."
        )
    elif current_val >= warning_threshold:
        if critical_hours is not None:
            explanation = (
                f"Currently above warning limit ({warning_threshold:.1f}%). Projected under current "
                f"utilization pattern (+{slope:.2f}%/h) to breach critical threshold ({critical_threshold:.1f}%) "
                f"in {critical_eta_text}."
            )
        else:
            explanation = (
                f"Currently above warning limit ({warning_threshold:.1f}%). Trend is currently steady or decreasing."
            )
    elif slope > 0.05:
        if critical_hours is not None and warning_hours is not None:
            explanation = (
                f"Based on current trend (+{slope:.2f}%/h, R²={r2:.2f}), warning breach projected in {warning_eta_text} "
                f"and critical threshold in {critical_eta_text}."
            )
        elif critical_hours is not None:
            explanation = (
                f"Based on current trend (+{slope:.2f}%/h), critical threshold projected in {critical_eta_text}."
            )
        else:
            explanation = f"Increasing at +{slope:.2f}%/h, but within safe operating headroom."
    elif slope < -0.05:
        explanation = f"Utilization is decreasing at {slope:.2f}%/h. Headroom is recovering."
    else:
        explanation = "Utilization is stable. No capacity threshold breach projected under current workload."

    return MetricForecast(
        metric_name=metric_col,
        display_name=display_name,
        current_value=current_val,
        recent_average=recent_avg,
        slope_per_hour=slope,
        r_squared=r2,
        warning_threshold=warning_threshold,
        critical_threshold=critical_threshold,
        warning_breach_hours=warning_hours,
        critical_breach_hours=critical_hours,
        warning_eta_text=warning_eta_text,
        critical_eta_text=critical_eta_text,
        status=status,
        projection_explanation=explanation,
    )


def generate_forecast_trajectory(
    df: pd.DataFrame,
    metric_col: str,
    slope_per_hour: float,
    current_value: float,
    horizon_hours: int = 12,
) -> pd.DataFrame:
    """Generate forward forecast projection points for chart visualization.
    
    Args:
        df: Historical DataFrame with 'timestamp' column.
        metric_col: Name of the metric column.
        slope_per_hour: Linear rate of change per hour.
        current_value: Current metric value at last timestamp.
        horizon_hours: Number of future hours to project.
        
    Returns:
        DataFrame with projected timestamps and forecast values.
    """
    last_timestamp = pd.to_datetime(df["timestamp"].iloc[-1])
    
    future_timestamps = [
        last_timestamp + pd.Timedelta(hours=i) for i in range(0, horizon_hours + 1)
    ]
    
    # Project: value = current + slope * hour (clamped to 0-100% for realistic bounded percentage)
    future_values = [
        min(100.0, max(0.0, current_value + slope_per_hour * i))
        for i in range(0, horizon_hours + 1)
    ]
    
    return pd.DataFrame({
        "timestamp": future_timestamps,
        f"{metric_col}_forecast": future_values,
    })


def analyze_all_metrics(
    df: pd.DataFrame,
    lookback_points: int = 12,
    warning_threshold: float = 75.0,
    critical_threshold: float = 90.0,
) -> Dict[str, MetricForecast]:
    """Run forecasting analysis across all core infrastructure metrics.
    
    Returns:
        Dictionary mapping metric key to MetricForecast object.
    """
    configs = [
        ("cpu_percent", "CPU Utilization"),
        ("memory_percent", "Memory Utilization"),
        ("network_percent", "Network Bandwidth"),
    ]
    
    results = {}
    for col, label in configs:
        if col in df.columns:
            results[col] = forecast_metric(
                df=df,
                metric_col=col,
                display_name=label,
                lookback_points=lookback_points,
                warning_threshold=warning_threshold,
                critical_threshold=critical_threshold,
            )
            
    return results
