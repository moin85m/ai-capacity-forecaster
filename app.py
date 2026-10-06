"""AI Capacity Forecaster - Streamlit Web Application.

A lightweight, production-grade infrastructure operations dashboard for SRE,
DevOps, and Cloud Engineering teams.
"""

import os
from datetime import datetime, timedelta
from typing import Dict, Tuple
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from src.ai_advisor import AIAdvisorResponse, query_llm_advisor, run_offline_advisory
from src.forecasting import (
    MetricForecast,
    analyze_all_metrics,
    generate_forecast_trajectory,
)
from src.recommendations import (
    RISK_COLORS,
    SystemRiskReport,
    evaluate_system_risk,
)

# -----------------------------------------------------------------------------
# Streamlit Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Capacity Forecaster | SRE Ops Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for high-end SRE Operations Aesthetic
st.markdown("""
<style>
    /* Metric Card Styling */
    .metric-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 16px 20px;
        color: #f8fafc;
        margin-bottom: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }
    .metric-title {
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #94a3b8;
        margin-bottom: 6px;
    }
    .metric-value {
        font-size: 2.1rem;
        font-weight: 700;
        line-height: 1.1;
        font-family: 'JetBrains Mono', monospace, sans-serif;
    }
    .metric-subtitle {
        font-size: 0.8rem;
        color: #94a3b8;
        margin-top: 6px;
    }
    .badge {
        display: inline-block;
        padding: 3px 8px;
        font-size: 0.72rem;
        font-weight: 700;
        border-radius: 4px;
        letter-spacing: 0.05em;
    }
    .badge-observed {
        background-color: #1e3a5f;
        color: #93c5fd;
        border: 1px solid #3b82f6;
    }
    .badge-heuristic {
        background-color: #3b2d54;
        color: #d8b4fe;
        border: 1px solid #a855f7;
    }
    .badge-ai {
        background-color: #064e3b;
        color: #6ee7b7;
        border: 1px solid #10b981;
    }
    .risk-banner {
        padding: 16px 20px;
        border-radius: 8px;
        font-weight: 600;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .code-box {
        background-color: #0f172a;
        border: 1px solid #334155;
        border-radius: 6px;
        padding: 10px 14px;
        font-family: monospace;
        font-size: 0.85rem;
        color: #38bdf8;
        overflow-x: auto;
    }
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Data Loading & Synthetic Scenarios
# -----------------------------------------------------------------------------
@st.cache_data
def load_csv_data(filepath: str) -> pd.DataFrame:
    """Load default CSV metrics dataset."""
    df = pd.read_csv(filepath)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def generate_synthetic_scenario(scenario_type: str) -> pd.DataFrame:
    """Generate dynamic simulated telemetry data for interactive demonstrations."""
    base_time = datetime.now() - timedelta(hours=48)
    timestamps = [base_time + timedelta(hours=i) for i in range(48)]
    np.random.seed(42)
    
    if scenario_type == "Memory Leak Simulation":
        cpu = np.clip(np.linspace(40, 65, 48) + np.random.normal(0, 1.5, 48), 20, 100)
        # Memory climbs monotonically from 50% to 94%
        memory = np.clip(np.linspace(50, 94, 48) + np.random.normal(0, 0.8, 48), 20, 100)
        network = np.clip(np.linspace(35, 45, 48) + np.random.normal(0, 1.5, 48), 20, 100)
        requests = np.clip(np.linspace(900, 1100, 48) + np.random.normal(0, 20, 48), 100, 5000)
        instances = [3] * 48
    elif scenario_type == "Sudden Traffic Spike":
        # Sudden surge in last 12 hours
        x = np.arange(48)
        spike = np.where(x < 36, 0, (x - 36) ** 1.8 * 2.5)
        cpu = np.clip(45 + spike + np.random.normal(0, 2, 48), 20, 100)
        memory = np.clip(55 + spike * 0.7 + np.random.normal(0, 1.5, 48), 20, 100)
        network = np.clip(35 + spike * 1.2 + np.random.normal(0, 2, 48), 20, 100)
        requests = np.clip(800 + spike * 40 + np.random.normal(0, 30, 48), 100, 5000)
        instances = [2 if i < 40 else 4 for i in range(48)]
    elif scenario_type == "Stable / Healthy State":
        cpu = np.clip(np.random.normal(42, 2.5, 48), 20, 60)
        memory = np.clip(np.random.normal(52, 2.0, 48), 30, 65)
        network = np.clip(np.random.normal(30, 2.0, 48), 15, 50)
        requests = np.clip(np.random.normal(850, 30, 48), 500, 1500)
        instances = [2] * 48
    else:  # Default Workload Growth
        cpu = np.clip(np.linspace(42, 92, 48) + np.random.normal(0, 1.2, 48), 20, 100)
        memory = np.clip(np.linspace(54, 87, 48) + np.random.normal(0, 1.0, 48), 20, 100)
        network = np.clip(np.linspace(31, 83, 48) + np.random.normal(0, 1.2, 48), 20, 100)
        requests = np.clip(np.linspace(800, 2540, 48) + np.random.normal(0, 25, 48), 500, 4000)
        instances = [2 if i < 30 else 3 for i in range(48)]
        
    return pd.DataFrame({
        "timestamp": timestamps,
        "cpu_percent": np.round(cpu, 1),
        "memory_percent": np.round(memory, 1),
        "network_percent": np.round(network, 1),
        "request_rate": np.round(requests, 0).astype(int),
        "active_instances": instances,
    })


# -----------------------------------------------------------------------------
# Sidebar: Configuration & Controls
# -----------------------------------------------------------------------------
with st.sidebar:
    st.title("⚡ Telemetry Controls")
    st.caption("AI Capacity Forecaster v1.0 • SRE Cockpit")
    
    st.markdown("---")
    st.subheader("📊 Scenario Selection")
    scenario = st.selectbox(
        "Simulation Scenario",
        [
            "Default (48h Workload Growth)",
            "Memory Leak Simulation",
            "Sudden Traffic Spike",
            "Stable / Healthy State",
            "Upload Custom CSV",
        ],
        index=0,
        help="Select a simulated infrastructure workload pattern or upload your own telemetry."
    )
    
    uploaded_file = None
    if scenario == "Upload Custom CSV":
        uploaded_file = st.file_uploader("Upload Telemetry CSV", type=["csv"])

    st.markdown("---")
    st.subheader("🎯 Capacity Thresholds")
    warning_thresh = st.slider(
        "Warning Threshold (%)",
        min_value=50,
        max_value=85,
        value=75,
        step=1,
        help="Alert threshold triggering elevated capacity monitoring."
    )
    critical_thresh = st.slider(
        "Critical Threshold (%)",
        min_value=80,
        max_value=98,
        value=90,
        step=1,
        help="Emergency capacity threshold requiring immediate remediation."
    )
    
    if warning_thresh >= critical_thresh:
        st.warning("⚠️ Warning threshold should be lower than critical threshold.")

    st.markdown("---")
    st.subheader("📈 Forecasting Parameters")
    lookback_hours = st.slider(
        "Lookback Trend Window (Hours)",
        min_value=4,
        max_value=24,
        value=12,
        step=1,
        help="Number of most recent hourly data points used to compute the linear regression slope."
    )
    forecast_horizon = st.slider(
        "Forecast Horizon (Hours Ahead)",
        min_value=4,
        max_value=24,
        value=12,
        step=1,
        help="Number of hours to project into the future on charts."
    )

    st.markdown("---")
    st.subheader("🤖 AI Advisor Mode")
    ai_mode_choice = st.radio(
        "Advisory Engine",
        [
            "Mode A — Offline Heuristic Engine (No API Key)",
            "Mode B — AI-Assisted LLM Mode",
        ],
        index=0,
    )
    
    user_api_key = ""
    llm_provider = "auto"
    if "Mode B" in ai_mode_choice:
        llm_provider = st.selectbox("LLM Provider", ["auto", "gemini", "openai"])
        user_api_key = st.text_input(
            "API Key (Optional / Env Var Fallback)",
            type="password",
            help="Leave blank to use GEMINI_API_KEY / OPENAI_API_KEY from environment, or enter key here. Keys are never saved.",
        )
        st.caption("🔒 Keys are held in memory only for the active session.")


# -----------------------------------------------------------------------------
# Data Loading Execution
# -----------------------------------------------------------------------------
default_csv_path = os.path.join(os.path.dirname(__file__), "data", "infrastructure_metrics.csv")

if scenario == "Upload Custom CSV" and uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    except Exception as e:
        st.error(f"Error parsing uploaded CSV: {e}")
        st.stop()
elif scenario == "Default (48h Workload Growth)" and os.path.exists(default_csv_path):
    df = load_csv_data(default_csv_path)
else:
    df = generate_synthetic_scenario(scenario)

# Ensure data is sorted
df = df.sort_values("timestamp").reset_index(drop=True)

# -----------------------------------------------------------------------------
# Analytics Computation
# -----------------------------------------------------------------------------
metric_forecasts = analyze_all_metrics(
    df=df,
    lookback_points=lookback_hours,
    warning_threshold=float(warning_thresh),
    critical_threshold=float(critical_thresh),
)

system_risk = evaluate_system_risk(metric_forecasts)

last_row = df.iloc[-1]
current_instances = int(last_row.get("active_instances", 2))
current_req_rate = float(last_row.get("request_rate", 0))

# -----------------------------------------------------------------------------
# Main Dashboard Header
# -----------------------------------------------------------------------------
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.title("⚡ AI Capacity Forecaster")
    st.markdown(
        "**Proactive SRE Infrastructure Operations & Capacity Saturation Predictor** • "
        f"Telemetry Window: Last {len(df)} hours (Hourly Resolution)"
    )

with col_h2:
    mode_badge_text = "Mode A: Offline Heuristic" if "Mode A" in ai_mode_choice else "Mode B: Live LLM"
    mode_badge_class = "badge-heuristic" if "Mode A" in ai_mode_choice else "badge-ai"
    st.markdown(
        f"""
        <div style="text-align: right; padding-top: 10px;">
            <span class="badge {mode_badge_class}">{mode_badge_text}</span>
            <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 4px;">
                Latest Telemetry: {df['timestamp'].iloc[-1].strftime('%Y-%m-%d %H:%M')}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# -----------------------------------------------------------------------------
# Top Level System Risk Banner
# -----------------------------------------------------------------------------
banner_bg = system_risk.overall_color
st.markdown(
    f"""
    <div class="risk-banner" style="background-color: {banner_bg}1a; border-left: 6px solid {banner_bg};">
        <div>
            <span style="font-size: 1.15rem; color: {banner_bg}; font-weight: 800; letter-spacing: 0.05em;">
                [{system_risk.overall_level} RISK]
            </span>
            <span style="color: #f8fafc; font-size: 1.05rem; margin-left: 10px;">
                {system_risk.summary_headline}
            </span>
        </div>
        <div>
            <span class="badge badge-observed">Observed Telemetry</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# Metric KPI Cards
# -----------------------------------------------------------------------------
col_kpi1, col_kpi2, col_kpi3, col_kpi4, col_kpi5 = st.columns(5)

cpu_f = metric_forecasts.get("cpu_percent")
mem_f = metric_forecasts.get("memory_percent")
net_f = metric_forecasts.get("network_percent")

def render_kpi(col, title, val_str, slope_val, eta_str, risk_level, unit="%"):
    color = RISK_COLORS.get(risk_level, "#94a3b8")
    slope_arrow = "▲" if slope_val > 0.01 else ("▼" if slope_val < -0.01 else "▶")
    slope_color = "#ef4444" if slope_val > 0.5 else ("#f59e0b" if slope_val > 0 else "#10b981")
    
    with col:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">{title}</div>
                <div class="metric-value" style="color: {color};">{val_str}{unit}</div>
                <div class="metric-subtitle">
                    <span style="color: {slope_color}; font-weight: 600;">{slope_arrow} {slope_val:+.2f}%/h</span>
                    <span style="float: right; color: #cbd5e1;">ETA: {eta_str}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

if cpu_f:
    render_kpi(col_kpi1, "CPU Utilization", f"{cpu_f.current_value:.1f}", cpu_f.slope_per_hour, cpu_f.critical_eta_text, system_risk.metric_risks["cpu_percent"].level)
if mem_f:
    render_kpi(col_kpi2, "Memory Utilization", f"{mem_f.current_value:.1f}", mem_f.slope_per_hour, mem_f.critical_eta_text, system_risk.metric_risks["memory_percent"].level)
if net_f:
    render_kpi(col_kpi3, "Network Bandwidth", f"{net_f.current_value:.1f}", net_f.slope_per_hour, net_f.critical_eta_text, system_risk.metric_risks["network_percent"].level)

with col_kpi4:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Ingress Rate</div>
            <div class="metric-value" style="color: #38bdf8;">{current_req_rate:,.0f}</div>
            <div class="metric-subtitle">requests / second</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_kpi5:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Active Replicas</div>
            <div class="metric-value" style="color: #a78bfa;">{current_instances}</div>
            <div class="metric-subtitle">healthy pods / nodes</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# -----------------------------------------------------------------------------
# Time Series & Forecasting Visualizations (Plotly)
# -----------------------------------------------------------------------------
st.markdown("### 📈 Time-Series Telemetry & Capacity Saturation Projections")

tab_all, tab_cpu, tab_mem, tab_net, tab_traffic = st.tabs([
    "📊 Multi-Metric Overview",
    "💻 CPU Deep Dive",
    "🧠 Memory Deep Dive",
    "🌐 Network Deep Dive",
    "🚀 Ingress & Replica Correlation",
])

# Multi-metric unified chart
with tab_all:
    fig_all = go.Figure()
    
    # 1. Historical curves
    fig_all.add_trace(go.Scatter(
        x=df["timestamp"], y=df["cpu_percent"],
        name="CPU (Observed)", mode="lines+markers",
        line=dict(color="#38bdf8", width=2.5),
        marker=dict(size=4),
    ))
    fig_all.add_trace(go.Scatter(
        x=df["timestamp"], y=df["memory_percent"],
        name="Memory (Observed)", mode="lines+markers",
        line=dict(color="#c084fc", width=2.5),
        marker=dict(size=4),
    ))
    fig_all.add_trace(go.Scatter(
        x=df["timestamp"], y=df["network_percent"],
        name="Network (Observed)", mode="lines+markers",
        line=dict(color="#34d399", width=2.5),
        marker=dict(size=4),
    ))
    
    # 2. Forward projections
    for col_name, color, label in [
        ("cpu_percent", "#38bdf8", "CPU"),
        ("memory_percent", "#c084fc", "Memory"),
        ("network_percent", "#34d399", "Network"),
    ]:
        f_obj = metric_forecasts.get(col_name)
        if f_obj:
            traj_df = generate_forecast_trajectory(
                df=df,
                metric_col=col_name,
                slope_per_hour=f_obj.slope_per_hour,
                current_value=f_obj.current_value,
                horizon_hours=forecast_horizon,
            )
            fig_all.add_trace(go.Scatter(
                x=traj_df["timestamp"],
                y=traj_df[f"{col_name}_forecast"],
                name=f"{label} (Projected)",
                mode="lines",
                line=dict(color=color, dash="dash", width=2),
                hoverinfo="x+y+name",
            ))

    # Threshold horizontal indicators
    fig_all.add_hline(
        y=warning_thresh, line_dash="dot", line_color="#f59e0b", line_width=1.5,
        annotation_text=f"Warning Threshold ({warning_thresh}%)",
        annotation_position="bottom right",
    )
    fig_all.add_hline(
        y=critical_thresh, line_dash="solid", line_color="#ef4444", line_width=2,
        annotation_text=f"Critical Threshold ({critical_thresh}%)",
        annotation_position="top right",
    )
    
    # Vertical marker at current time (boundary between observed and projected)
    current_time_marker = df["timestamp"].iloc[-1]
    fig_all.add_vline(
        x=current_time_marker, line_dash="dashdot", line_color="#94a3b8", line_width=1.5,
        annotation_text="← Observed Telemetry | Projected Forecast →",
        annotation_position="top left",
    )

    fig_all.update_layout(
        template="plotly_dark",
        height=480,
        margin=dict(l=40, r=40, t=30, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis_title="Timeline",
        yaxis_title="Utilization Percentage (%)",
        yaxis=dict(range=[0, 105]),
        hovermode="x unified",
    )
    st.plotly_chart(fig_all, use_container_width=True)


def build_single_metric_fig(metric_col: str, title: str, color_hex: str):
    f = metric_forecasts[metric_col]
    traj = generate_forecast_trajectory(
        df=df,
        metric_col=metric_col,
        slope_per_hour=f.slope_per_hour,
        current_value=f.current_value,
        horizon_hours=forecast_horizon,
    )
    fig = go.Figure()
    
    # Historical
    fig.add_trace(go.Scatter(
        x=df["timestamp"], y=df[metric_col],
        name=f"Observed {title}",
        line=dict(color=color_hex, width=3),
        mode="lines+markers",
    ))
    
    # Linear projection
    fig.add_trace(go.Scatter(
        x=traj["timestamp"], y=traj[f"{metric_col}_forecast"],
        name=f"Projected {title} (+{f.slope_per_hour:.2f}%/h)",
        line=dict(color=color_hex, dash="dash", width=2.5),
        mode="lines",
    ))
    
    fig.add_hline(y=warning_thresh, line_dash="dot", line_color="#f59e0b", annotation_text=f"Warning ({warning_thresh}%)")
    fig.add_hline(y=critical_thresh, line_dash="solid", line_color="#ef4444", annotation_text=f"Critical ({critical_thresh}%)")
    fig.add_vline(x=df["timestamp"].iloc[-1], line_dash="dashdot", line_color="#64748b", annotation_text="Forecast Horizon Start")
    
    fig.update_layout(
        template="plotly_dark",
        height=420,
        title=f"{title} Linear Regression Forecast (R² = {f.r_squared:.2f})",
        xaxis_title="Timestamp",
        yaxis_title="Utilization (%)",
        yaxis=dict(range=[0, 105]),
    )
    return fig

with tab_cpu:
    st.plotly_chart(build_single_metric_fig("cpu_percent", "CPU Utilization", "#38bdf8"), use_container_width=True)
    st.info(f"💡 **CPU Forecast Note**: {cpu_f.projection_explanation}")

with tab_mem:
    st.plotly_chart(build_single_metric_fig("memory_percent", "Memory Utilization", "#c084fc"), use_container_width=True)
    st.info(f"💡 **Memory Forecast Note**: {mem_f.projection_explanation}")

with tab_net:
    st.plotly_chart(build_single_metric_fig("network_percent", "Network Bandwidth", "#34d399"), use_container_width=True)
    st.info(f"💡 **Network Forecast Note**: {net_f.projection_explanation}")

with tab_traffic:
    fig_corr = make_subplots(specs=[[{"secondary_y": True}]])
    fig_corr.add_trace(
        go.Scatter(x=df["timestamp"], y=df["request_rate"], name="Request Rate (req/s)", line=dict(color="#f43f5e", width=2.5)),
        secondary_y=False,
    )
    fig_corr.add_trace(
        go.Scatter(x=df["timestamp"], y=df["active_instances"], name="Active Replicas", line=dict(color="#fbbf24", width=2.5, shape="hv")),
        secondary_y=True,
    )
    fig_corr.update_layout(
        template="plotly_dark",
        height=420,
        title="Ingress Workload vs Autoscaling Response",
    )
    fig_corr.update_xaxes(title_text="Timestamp")
    fig_corr.update_yaxes(title_text="Requests per Second", secondary_y=False)
    fig_corr.update_yaxes(title_text="Active Pod Instances", secondary_y=True)
    st.plotly_chart(fig_corr, use_container_width=True)


# -----------------------------------------------------------------------------
# Capacity Breakdown & Risk Summary Table
# -----------------------------------------------------------------------------
st.markdown("### 📋 Capacity Forecast & Risk Breakdown")

summary_table_data = []
for key, f in metric_forecasts.items():
    risk = system_risk.metric_risks[key]
    summary_table_data.append({
        "Resource Metric": f.display_name,
        "Current Value": f"{f.current_value:.1f}%",
        "Recent Avg (12h)": f"{f.recent_average:.1f}%",
        "Linear Slope": f"{f.slope_per_hour:+.2f}% / hr",
        "Confidence (R²)": f"{f.r_squared:.2f}",
        "Warning ETA": f.warning_eta_text,
        "Critical ETA": f.critical_eta_text,
        "Risk Level": risk.level,
        "Current Status": f.status.replace("_", " ").title(),
    })

summary_df = pd.DataFrame(summary_table_data)
st.dataframe(
    summary_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Resource Metric": st.column_config.TextColumn(width="medium"),
        "Risk Level": st.column_config.TextColumn(width="small"),
    }
)

st.caption("ℹ️ *Linear projections extrapolate recent growth trends. Threshold breach estimates are non-guaranteed projections under current workload dynamics.*")


# -----------------------------------------------------------------------------
# Operational Recommendations & SRE Runbook
# -----------------------------------------------------------------------------
st.markdown("---")
st.markdown("### 🛠️ SRE Remediation Runbooks & Operational Actions")

col_rec1, col_rec2 = st.columns([1, 1])

with col_rec1:
    st.markdown(
        """
        <div style="margin-bottom: 8px;">
            <span class="badge badge-heuristic">Deterministic Engine</span>
            <span style="font-size: 1.1rem; font-weight: 700; margin-left: 8px;">🚨 Immediate Actions</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    if system_risk.immediate_actions:
        for idx, act in enumerate(system_risk.immediate_actions):
            urg_color = "#ef4444" if "IMMEDIATE" in act.urgency else "#f97316"
            with st.expander(f"[{act.urgency}] {act.title}", expanded=(idx == 0)):
                st.markdown(f"**Target**: `{act.target_metric}` | **Category**: `{act.category}`")
                st.write(act.description)
                st.markdown("**Runbook Command Execution:**")
                st.code("\n".join(act.runbook_commands), language="bash")
                st.caption(f"🧠 **SRE Rationale**: {act.reasoning}")
    else:
        st.success("✅ No immediate P1/P2 actions required. System capacity is operating within safe limits.")

with col_rec2:
    st.markdown(
        """
        <div style="margin-bottom: 8px;">
            <span class="badge badge-heuristic">Deterministic Engine</span>
            <span style="font-size: 1.1rem; font-weight: 700; margin-left: 8px;">🛡️ Preventative & Tuning Actions</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    for idx, act in enumerate(system_risk.preventative_actions):
        with st.expander(f"[{act.urgency}] {act.title}", expanded=False):
            st.markdown(f"**Target**: `{act.target_metric}` | **Category**: `{act.category}`")
            st.write(act.description)
            st.markdown("**Command / Validation Template:**")
            st.code("\n".join(act.runbook_commands), language="bash")
            st.caption(f"🧠 **SRE Rationale**: {act.reasoning}")


# -----------------------------------------------------------------------------
# AI Operations Advisor (Mode A vs Mode B)
# -----------------------------------------------------------------------------
st.markdown("---")
st.markdown("### 🤖 AI Capacity Operations Advisor")

st.markdown(
    """
    <div style="font-size: 0.9rem; color: #94a3b8; margin-bottom: 15px;">
        Evaluates system metrics, slope trajectory, and threshold timing to generate synthesized operational intelligence.
        Supports <strong>Mode A (Offline Deterministic Heuristics)</strong> and <strong>Mode B (LLM Synthesis)</strong>.
    </div>
    """,
    unsafe_allow_html=True,
)

col_ai_btn, col_ai_badge = st.columns([1, 3])
with col_ai_btn:
    generate_ai = st.button("⚡ Generate AI Incident Advisory", type="primary", use_container_width=True)

# Generate or read cached advisor response
if generate_ai or "ai_advisor_cache" not in st.session_state:
    with st.spinner("Generating capacity interpretation and SRE recommendations..."):
        if "Mode B" in ai_mode_choice:
            advisory_result = query_llm_advisor(
                metrics=metric_forecasts,
                risk_report=system_risk,
                api_key=user_api_key if user_api_key.strip() else None,
                provider=llm_provider,
                active_instances=current_instances,
                request_rate=current_req_rate,
            )
        else:
            advisory_result = run_offline_advisory(
                metrics=metric_forecasts,
                risk_report=system_risk,
            )
        st.session_state["ai_advisor_cache"] = advisory_result

advisory: AIAdvisorResponse = st.session_state["ai_advisor_cache"]

# Display Advisor Output Container
badge_cls = "badge-ai" if advisory.is_live_llm else "badge-heuristic"
st.markdown(
    f"""
    <div style="background-color: #0f172a; border: 1px solid #334155; border-radius: 10px; padding: 20px; margin-top: 10px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
            <div>
                <span class="badge {badge_cls}">{advisory.mode}</span>
                <span style="font-size: 0.85rem; color: #94a3b8; margin-left: 10px;">Provider: {advisory.provider}</span>
            </div>
            <div>
                <span class="badge badge-observed">Input: Verified Telemetry</span>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

ai_col1, ai_col2 = st.columns(2)

with ai_col1:
    st.markdown("#### 1. 🔍 Capacity Interpretation")
    st.write(advisory.capacity_interpretation)
    
    st.markdown("#### 2. ⚠️ Risk Assessment")
    st.markdown(advisory.risk_assessment)

    st.markdown("#### 3. ⏱️ Forecast Explanation")
    st.markdown(advisory.forecast_explanation)

with ai_col2:
    st.markdown("#### 4. 🚀 Scaling Recommendation")
    st.markdown(advisory.scaling_recommendation)
    
    st.markdown("#### 5. 🏗️ Architectural Optimization Suggestions")
    for opt in advisory.optimization_suggestions:
        st.markdown(f"- {opt}")

st.markdown("---")

# -----------------------------------------------------------------------------
# Raw Telemetry Data Explorer
# -----------------------------------------------------------------------------
with st.expander("📁 Raw Infrastructure Telemetry Data Explorer"):
    st.markdown("**Underlying 48-Hour Hourly Observations:**")
    st.dataframe(df, use_container_width=True)
    
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Telemetry CSV",
        data=csv_bytes,
        file_name="infrastructure_metrics_telemetry.csv",
        mime="text/csv",
    )
