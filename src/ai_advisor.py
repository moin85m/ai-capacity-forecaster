"""AI SRE Operations Advisor Module.

Provides dual-mode capacity interpretation:
- Mode A (Offline / Demo Mode): Rich deterministic heuristic analysis (no API key required).
- Mode B (AI-Assisted Mode): LLM-powered incident interpretation, capacity forecasting explanation,
  and architecture scaling guidance using Gemini or OpenAI models.
"""

import os
from dataclasses import dataclass
from typing import Dict, List, Optional
from src.forecasting import MetricForecast
from src.recommendations import SystemRiskReport


@dataclass
class AIAdvisorResponse:
    """Structured response from the SRE Advisor."""
    mode: str  # "Mode A (Offline Deterministic)" or "Mode B (AI LLM Assisted)"
    provider: str  # "Local Heuristic Engine", "Google Gemini", or "OpenAI"
    capacity_interpretation: str
    risk_assessment: str
    forecast_explanation: str
    scaling_recommendation: str
    optimization_suggestions: List[str]
    is_live_llm: bool


SYSTEM_PROMPT = """You are a Principal Site Reliability Engineer (SRE) and Cloud Infrastructure Architect.
Analyze the provided telemetry metrics and linear capacity forecast.
Provide a concise, professional operational assessment suitable for an SRE incident response room or capacity planning review.

Structure your response into 5 distinct sections with clear markdown headers:
1. ### Capacity Interpretation
2. ### Risk Assessment
3. ### Forecast Explanation
4. ### Scaling Recommendation (Include specific CLI/Kubernetes/Cloud commands)
5. ### Architectural Optimization Suggestions (3-4 bullet points)

Maintain a calm, pragmatic, operations-focused tone. Clearly distinguish between hard observed telemetry and your analytical projections.
"""


def format_telemetry_payload(
    metrics: Dict[str, MetricForecast],
    risk_report: SystemRiskReport,
    active_instances: Optional[int] = None,
    request_rate: Optional[float] = None,
) -> str:
    """Format summarized telemetry and linear trend results into an LLM prompt payload."""
    payload_lines = [
        "=== INFRASTRUCTURE TELEMETRY SUMMARY ===",
        f"Overall System Risk: {risk_report.overall_level} (Dominant Stress: {risk_report.dominant_metric})",
    ]
    
    if active_instances is not None:
        payload_lines.append(f"Current Active Instances / Nodes: {active_instances}")
    if request_rate is not None:
        payload_lines.append(f"Current Ingress Request Rate: {request_rate:.0f} req/sec")
        
    payload_lines.append("\n--- METRIC VECTOR TELEMETRY ---")
    for key, f in metrics.items():
        payload_lines.append(
            f"• {f.display_name} ({f.metric_name}):\n"
            f"   - Current Observed: {f.current_value:.1f}%\n"
            f"   - Recent Lookback Average: {f.recent_average:.1f}%\n"
            f"   - Linear Trend Slope: {f.slope_per_hour:+.2f}% / hour (R² = {f.r_squared:.2f})\n"
            f"   - Warning Threshold ({f.warning_threshold:.1f}%): ETA = {f.warning_eta_text}\n"
            f"   - Critical Threshold ({f.critical_threshold:.1f}%): ETA = {f.critical_eta_text}\n"
            f"   - Status Flag: {f.status}"
        )
        
    payload_lines.append("\n--- RULE-BASED ENGINE OBSERVATIONS ---")
    for fact in risk_report.observed_facts:
        payload_lines.append(f"  [OBSERVED] {fact}")
        
    return "\n".join(payload_lines)


def run_offline_advisory(
    metrics: Dict[str, MetricForecast],
    risk_report: SystemRiskReport,
) -> AIAdvisorResponse:
    """Generate high-quality deterministic advisory report without calling any external API."""
    cpu_f = metrics.get("cpu_percent")
    mem_f = metrics.get("memory_percent")
    net_f = metrics.get("network_percent")
    
    # Capacity Interpretation
    interp_parts = []
    if risk_report.overall_level in ["CRITICAL", "HIGH"]:
        interp_parts.append(
            f"Infrastructure capacity is operating under severe stress, dominated by {risk_report.dominant_metric}. "
            f"Utilization is outpacing nominal baseline thresholds due to steady sustained traffic escalation."
        )
    elif risk_report.overall_level == "MEDIUM":
        interp_parts.append(
            f"Infrastructure capacity shows moderate strain on {risk_report.dominant_metric}. "
            f"Current headroom remains viable for standard operational buffers, but sustained upward trajectory threatens stability."
        )
    else:
        interp_parts.append(
            "All core subsystems (Compute, Memory, Network) operate with healthy operational headroom (>40% buffer)."
        )

    if cpu_f:
        interp_parts.append(
            f"CPU is at {cpu_f.current_value:.1f}% (moving at {cpu_f.slope_per_hour:+.2f}%/h)."
        )
    if mem_f:
        interp_parts.append(
            f"Memory utilization stands at {mem_f.current_value:.1f}% (moving at {mem_f.slope_per_hour:+.2f}%/h)."
        )
    if net_f:
        interp_parts.append(
            f"Network bandwidth is at {net_f.current_value:.1f}% (moving at {net_f.slope_per_hour:+.2f}%/h)."
        )

    capacity_interpretation = " ".join(interp_parts)

    # Risk Assessment
    risk_assessment = (
        f"**Severity Level: {risk_report.overall_level}**\n\n"
        f"The primary driver is **{risk_report.dominant_metric}**. "
        f"Under current regression slopes, available capacity headroom will reach exhaustion if unmitigated. "
        f"Immediate operational intervention is recommended to avoid cascaded container restarts and tail-latency SLA breaches."
    )

    # Forecast Explanation
    forecast_parts = []
    for f in [cpu_f, mem_f, net_f]:
        if f:
            if f.critical_breach_hours is not None and f.critical_breach_hours <= 6.0:
                forecast_parts.append(
                    f"- **{f.display_name}**: Critical breach projected in **{f.critical_eta_text}** "
                    f"(rate of growth: +{f.slope_per_hour:.2f}%/hr, R²={f.r_squared:.2f})."
                )
            elif f.warning_breach_hours is not None and f.warning_breach_hours <= 6.0:
                forecast_parts.append(
                    f"- **{f.display_name}**: Warning threshold breach projected in **{f.warning_eta_text}** "
                    f"(rate of growth: +{f.slope_per_hour:.2f}%/hr)."
                )
            else:
                forecast_parts.append(
                    f"- **{f.display_name}**: Headroom adequate; no critical breach projected in near term."
                )
    forecast_explanation = "\n".join(forecast_parts)

    # Scaling Recommendation
    scaling_lines = [
        "Execute immediate horizontal or vertical capacity adjustments to restore headroom:\n",
        "```bash",
        "# 1. Scale out application replicas:",
        "kubectl scale deployment/api-gateway --replicas=6",
        "",
        "# 2. Verify Horizontal Pod Autoscaler status and active metrics:",
        "kubectl get hpa api-gateway",
        "",
        "# 3. Verify node pool headroom in cluster:",
        "kubectl get nodes -o wide",
        "```"
    ]
    scaling_recommendation = "\n".join(scaling_lines)

    # Architectural Optimization Suggestions
    optimizations = [
        "**Implement Predictive Autoscaling**: Transition from reactive CPU-threshold scaling to predictive metric-based scaling (e.g. AWS Predictive Scaling or KEDA with Prometheus query triggers).",
        "**Offload API Payloads to Edge CDN**: Route static assets and cacheable JSON endpoints through Cloudflare / CloudFront to suppress 30-40% of ingress compute overhead.",
        "**Tune Garbage Collection & Connection Pools**: Audit container heap settings and database connection pool ceilings to curb monotonic memory climb.",
        "**Establish Multi-AZ Capacity Reserves**: Keep warm standby capacity (minimum 25% buffer) across secondary availability zones for fast failover.",
    ]

    return AIAdvisorResponse(
        mode="Mode A (Demo / Offline Mode)",
        provider="Local Deterministic Heuristic Engine",
        capacity_interpretation=capacity_interpretation,
        risk_assessment=risk_assessment,
        forecast_explanation=forecast_explanation,
        scaling_recommendation=scaling_recommendation,
        optimization_suggestions=optimizations,
        is_live_llm=False,
    )


def query_llm_advisor(
    metrics: Dict[str, MetricForecast],
    risk_report: SystemRiskReport,
    api_key: Optional[str] = None,
    provider: str = "auto",  # "gemini", "openai", or "auto"
    active_instances: Optional[int] = None,
    request_rate: Optional[float] = None,
) -> AIAdvisorResponse:
    """Analyze infrastructure telemetry using LLM if key is available, else fallback to Mode A.
    
    Safe API Key Resolution:
    1. Explicit `api_key` argument from user input.
    2. Environment variables: GEMINI_API_KEY, GOOGLE_API_KEY, OPENAI_API_KEY.
    3. Streamlit secrets (if running inside Streamlit).
    """
    # Resolve keys from environment if not passed explicitly
    gemini_key = api_key if (api_key and "AIza" in api_key) else (
        os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    )
    openai_key = api_key if (api_key and api_key.startswith("sk-")) else os.getenv("OPENAI_API_KEY")
    
    # Check general key if provider is explicit
    if api_key and not gemini_key and not openai_key:
        if provider == "openai":
            openai_key = api_key
        else:
            gemini_key = api_key

    telemetry_payload = format_telemetry_payload(
        metrics=metrics,
        risk_report=risk_report,
        active_instances=active_instances,
        request_rate=request_rate,
    )

    full_prompt = f"{SYSTEM_PROMPT}\n\nHere is the current live telemetry:\n\n{telemetry_payload}"

    # Try Gemini if key available
    if gemini_key and provider in ["gemini", "auto"]:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(full_prompt)
            text = response.text
            return parse_llm_markdown_response(text, provider_name="Google Gemini 1.5 Flash")
        except Exception as e:
            # If Gemini fails, log or try next
            pass

    # Try OpenAI if key available
    if openai_key and provider in ["openai", "auto"]:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Telemetry Data:\n\n{telemetry_payload}"},
                ],
                temperature=0.2,
            )
            text = completion.choices[0].message.content or ""
            return parse_llm_markdown_response(text, provider_name="OpenAI GPT-4o-mini")
        except Exception as e:
            pass

    # Fallback: Mode A (Deterministic)
    return run_offline_advisory(metrics, risk_report)


def parse_llm_markdown_response(markdown_text: str, provider_name: str) -> AIAdvisorResponse:
    """Parse structured markdown response from LLM into sections."""
    sections = {
        "capacity": "",
        "risk": "",
        "forecast": "",
        "scaling": "",
        "optimizations": [],
    }
    
    current_section = None
    lines = markdown_text.split("\n")
    
    for line in lines:
        lower = line.strip().lower()
        if "capacity interpretation" in lower:
            current_section = "capacity"
            continue
        elif "risk assessment" in lower:
            current_section = "risk"
            continue
        elif "forecast explanation" in lower:
            current_section = "forecast"
            continue
        elif "scaling recommendation" in lower:
            current_section = "scaling"
            continue
        elif "optimization suggestion" in lower or "architectural optimization" in lower:
            current_section = "optimizations"
            continue
            
        if current_section == "capacity":
            sections["capacity"] += line + "\n"
        elif current_section == "risk":
            sections["risk"] += line + "\n"
        elif current_section == "forecast":
            sections["forecast"] += line + "\n"
        elif current_section == "scaling":
            sections["scaling"] += line + "\n"
        elif current_section == "optimizations":
            if line.strip().startswith(("-", "*", "1.", "2.", "3.", "4.")):
                sections["optimizations"].append(line.strip().lstrip("-*0123456789. "))

    if not sections["capacity"].strip():
        # Fallback if markdown didn't match standard headings
        sections["capacity"] = markdown_text[:400]
        sections["risk"] = "See analysis report above."
        sections["forecast"] = "See model output details above."
        sections["scaling"] = "Execute autoscaling according to load profile."
        sections["optimizations"] = ["Review proactive capacity limits.", "Configure alerts."]

    return AIAdvisorResponse(
        mode="Mode B (AI-Assisted Mode)",
        provider=provider_name,
        capacity_interpretation=sections["capacity"].strip(),
        risk_assessment=sections["risk"].strip(),
        forecast_explanation=sections["forecast"].strip(),
        scaling_recommendation=sections["scaling"].strip(),
        optimization_suggestions=sections["optimizations"] or [
            "Enable horizontal pod autoscaling tuned to leading metric trends.",
            "Implement edge caching to shave off 25-35% of peak compute spikes."
        ],
        is_live_llm=True,
    )
