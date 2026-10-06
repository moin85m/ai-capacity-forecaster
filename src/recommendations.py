"""Risk Classification and Recommendation Engine.

Provides transparent rule-based risk classification and actionable operational
remediation runbooks for infrastructure, DevOps, and SRE teams.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from src.forecasting import MetricForecast


@dataclass
class MetricRisk:
    """Risk assessment for an individual metric."""
    metric_name: str
    display_name: str
    level: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    score: int  # 1 (Low) to 4 (Critical)
    rationale: str
    color_hex: str


@dataclass
class OperationalAction:
    """Actionable operational recommendation."""
    title: str
    category: str  # "SCALING", "RESOURCE_RESIZING", "TRAFFIC_MANAGEMENT", "INVESTIGATION"
    urgency: str   # "P1_IMMEDIATE", "P2_ELEVATED", "P3_PROACTIVE", "ROUTINE"
    description: str
    runbook_commands: List[str]
    reasoning: str
    target_metric: str


@dataclass
class SystemRiskReport:
    """System-wide risk assessment and operational recommendations."""
    overall_level: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    overall_color: str
    dominant_metric: str
    summary_headline: str
    metric_risks: Dict[str, MetricRisk]
    immediate_actions: List[OperationalAction]
    preventative_actions: List[OperationalAction]
    observed_facts: List[str]
    rule_reasoning: List[str]


RISK_COLORS = {
    "LOW": "#10B981",       # Emerald green
    "MEDIUM": "#F59E0B",    # Amber
    "HIGH": "#F97316",      # Vivid Orange
    "CRITICAL": "#EF4444",  # Crimson Red
}


def classify_metric_risk(forecast: MetricForecast) -> MetricRisk:
    """Transparently evaluate risk level for a single capacity metric.
    
    Risk Criteria:
    - CRITICAL: Current >= critical_threshold OR critical breach in <= 1.0 hour
    - HIGH: Current >= warning_threshold OR critical breach in <= 2.5 hours
    - MEDIUM: Current between 60% and warning_threshold with positive slope OR breach in <= 6 hours
    - LOW: Current < 60% and stable/decreasing OR no near-term breach
    """
    val = forecast.current_value
    slope = forecast.slope_per_hour
    crit_hrs = forecast.critical_breach_hours
    warn_hrs = forecast.warning_breach_hours
    warn_thresh = forecast.warning_threshold
    crit_thresh = forecast.critical_threshold

    # Rule 1: CRITICAL
    if val >= crit_thresh:
        return MetricRisk(
            metric_name=forecast.metric_name,
            display_name=forecast.display_name,
            level="CRITICAL",
            score=4,
            rationale=f"Utilization ({val:.1f}%) already exceeded critical threshold ({crit_thresh:.1f}%).",
            color_hex=RISK_COLORS["CRITICAL"],
        )
    if crit_hrs is not None and crit_hrs <= 1.0:
        return MetricRisk(
            metric_name=forecast.metric_name,
            display_name=forecast.display_name,
            level="CRITICAL",
            score=4,
            rationale=f"Critical threshold breach projected within {forecast.critical_eta_text} at +{slope:.2f}%/h.",
            color_hex=RISK_COLORS["CRITICAL"],
        )

    # Rule 2: HIGH
    if val >= warn_thresh:
        eta_desc = f" (Critical breach in {forecast.critical_eta_text})" if crit_hrs is not None else ""
        return MetricRisk(
            metric_name=forecast.metric_name,
            display_name=forecast.display_name,
            level="HIGH",
            score=3,
            rationale=f"Utilization ({val:.1f}%) exceeded warning threshold ({warn_thresh:.1f}%){eta_desc}.",
            color_hex=RISK_COLORS["HIGH"],
        )
    if crit_hrs is not None and crit_hrs <= 2.5:
        return MetricRisk(
            metric_name=forecast.metric_name,
            display_name=forecast.display_name,
            level="HIGH",
            score=3,
            rationale=f"Critical breach projected within {forecast.critical_eta_text} (+{slope:.2f}%/h).",
            color_hex=RISK_COLORS["HIGH"],
        )
    if warn_hrs is not None and warn_hrs <= 1.5:
        return MetricRisk(
            metric_name=forecast.metric_name,
            display_name=forecast.display_name,
            level="HIGH",
            score=3,
            rationale=f"Warning threshold breach imminent in {forecast.warning_eta_text}.",
            color_hex=RISK_COLORS["HIGH"],
        )

    # Rule 3: MEDIUM
    if (val >= 60.0 and slope > 0.1) or (warn_hrs is not None and warn_hrs <= 6.0):
        eta = forecast.warning_eta_text if warn_hrs is not None else "extended hours"
        return MetricRisk(
            metric_name=forecast.metric_name,
            display_name=forecast.display_name,
            level="MEDIUM",
            score=2,
            rationale=f"Utilization is elevated ({val:.1f}%) with upward growth (+{slope:.2f}%/h). Warning breach in {eta}.",
            color_hex=RISK_COLORS["MEDIUM"],
        )

    # Rule 4: LOW
    return MetricRisk(
        metric_name=forecast.metric_name,
        display_name=forecast.display_name,
        level="LOW",
        score=1,
        rationale=f"Utilization is safe ({val:.1f}%) and stable ({slope:+.2f}%/h). No near-term breach projected.",
        color_hex=RISK_COLORS["LOW"],
    )


def build_cpu_recommendations(forecast: MetricForecast, risk: MetricRisk) -> List[OperationalAction]:
    """Generate CPU-specific SRE actions based on risk level and slope."""
    actions = []
    
    if risk.level in ["CRITICAL", "HIGH"]:
        actions.append(OperationalAction(
            title="Trigger Horizontal Pod / Instance Autoscaling",
            category="SCALING",
            urgency="P1_IMMEDIATE" if risk.level == "CRITICAL" else "P2_ELEVATED",
            description=(
                f"Scale out workload compute replicas immediately. Current CPU is {forecast.current_value:.1f}% "
                f"with a steep growth rate of +{forecast.slope_per_hour:.2f}%/h."
            ),
            runbook_commands=[
                "# Kubernetes horizontal scale-out:",
                "kubectl scale deployment/api-gateway --replicas=6",
                "# AWS EC2 / ECS autoscaling override:",
                "aws autoscaling set-desired-capacity --auto-scaling-group-name prod-web-asg --desired-capacity 6",
            ],
            reasoning=(
                f"Adding compute instances redistributes ingress CPU load across a wider pool, "
                f"lowering per-node CPU by an estimated ~30-40% within minutes."
            ),
            target_metric="CPU",
        ))
        
        actions.append(OperationalAction(
            title="Inspect CPU Profiling & Heavy Thread Execution",
            category="INVESTIGATION",
            urgency="P2_ELEVATED",
            description="Collect async profiler dumps to detect unoptimized worker loops or query serialization.",
            runbook_commands=[
                "# Thread dump / top process inspection:",
                "kubectl exec -it <pod-id> -- jcmd 1 Thread.print > thread_dump.txt",
                "top -b -n 1 -H | head -n 25",
            ],
            reasoning="Differentiates legitimate traffic growth from thread locks or CPU-bound algorithmic regressions.",
            target_metric="CPU",
        ))
    elif risk.level == "MEDIUM":
        actions.append(OperationalAction(
            title="Verify HPA Thresholds & Prepare Buffer Capacity",
            category="SCALING",
            urgency="P3_PROACTIVE",
            description="Review Horizontal Pod Autoscaler targets to ensure scaling triggers before 75% saturation.",
            runbook_commands=[
                "kubectl get hpa api-gateway -o yaml",
                "kubectl patch hpa api-gateway -p '{\"spec\":{\"targetCPUUtilizationPercentage\":70}}'",
            ],
            reasoning="Ensures automatic scale-up activates proactively before critical latency degradation occurs.",
            target_metric="CPU",
        ))
        
    return actions


def build_memory_recommendations(forecast: MetricForecast, risk: MetricRisk) -> List[OperationalAction]:
    """Generate Memory-specific SRE actions."""
    actions = []
    
    if risk.level in ["CRITICAL", "HIGH"]:
        actions.append(OperationalAction(
            title="Expand Node Memory Limits & Worker Heap Boundaries",
            category="RESOURCE_RESIZING",
            urgency="P1_IMMEDIATE" if risk.level == "CRITICAL" else "P2_ELEVATED",
            description=(
                f"Current memory allocation is at {forecast.current_value:.1f}%. Apply vertical memory quota "
                f"increases to prevent Out-Of-Memory (OOM-Killed) pod terminations."
            ),
            runbook_commands=[
                "# Increase container memory limits:",
                "kubectl set resources deployment/api-gateway --limits=memory=8Gi --requests=memory=6Gi",
                "# Check OOM kill events in dmesg:",
                "kubectl get events --field-selector reason=OOMKilled -A",
            ],
            reasoning="OOM events cause sudden cascaded node failovers. Increasing headroom buys time for diagnostic profiling.",
            target_metric="Memory",
        ))
        
        actions.append(OperationalAction(
            title="Investigate Memory Leak & Flush In-Memory Caches",
            category="INVESTIGATION",
            urgency="P2_ELEVATED",
            description="Check garbage collection telemetry, cache eviction policies (TTL/LRU), and leak patterns.",
            runbook_commands=[
                "# Inspect container memory cgroups:",
                "cat /sys/fs/cgroup/memory/memory.stat | grep -E 'hierarchical_memory_limit|total_rss'",
                "# Flush application Redis/Memcached volatile keys:",
                "redis-cli -h cache.internal MEMORY USAGE hot_session_keys",
            ],
            reasoning="A monotonic memory slope without plateau frequently indicates cache bloat or uncollected heap leaks.",
            target_metric="Memory",
        ))
    elif risk.level == "MEDIUM":
        actions.append(OperationalAction(
            title="Audit Memory Allocation Headroom & GC Pause Times",
            category="RESOURCE_RESIZING",
            urgency="P3_PROACTIVE",
            description="Audit JVM/Node/Go GC pause times and adjust memory request-to-limit ratio.",
            runbook_commands=[
                "kubectl top pods -l app=api-gateway --sort-by=memory",
            ],
            reasoning="Preventative memory right-sizing eliminates silent swapping and tail latency spikes.",
            target_metric="Memory",
        ))
        
    return actions


def build_network_recommendations(forecast: MetricForecast, risk: MetricRisk) -> List[OperationalAction]:
    """Generate Network-specific SRE actions."""
    actions = []
    
    if risk.level in ["CRITICAL", "HIGH"]:
        actions.append(OperationalAction(
            title="Enable Edge CDN Caching & Connection Keep-Alive",
            category="TRAFFIC_MANAGEMENT",
            urgency="P2_ELEVATED",
            description=(
                f"Network bandwidth utilization is {forecast.current_value:.1f}% (rising at +{forecast.slope_per_hour:.2f}%/h). "
                f"Offload high-volume static assets and API payloads to edge CDN."
            ),
            runbook_commands=[
                "# Enable response compression & caching on ingress controller:",
                "kubectl annotate ingress api-ingress nginx.ingress.kubernetes.io/enable-gzip='true' --overwrite",
                "# Verify connection socket counts:",
                "netstat -an | grep ESTABLISHED | wc -l",
            ],
            reasoning="Edge caching absorbs repetitive egress payload transfers, reducing VPC interface network saturation.",
            target_metric="Network",
        ))
        
        actions.append(OperationalAction(
            title="Implement Rate Limiting & Egress Traffic Shaping",
            category="TRAFFIC_MANAGEMENT",
            urgency="P2_ELEVATED",
            description="Enforce ingress token-bucket rate limits on non-critical endpoints to shield core services.",
            runbook_commands=[
                "# Apply API gateway rate limiting policy:",
                "kubectl annotate ingress api-ingress nginx.ingress.kubernetes.io/limit-rps='150' --overwrite",
            ],
            reasoning="Protects downstream NIC bandwidth from abusive crawlers or unthrottled batch sync workloads.",
            target_metric="Network",
        ))
    elif risk.level == "MEDIUM":
        actions.append(OperationalAction(
            title="Monitor VPC Flow Logs & High-Bandwidth Peering Links",
            category="INVESTIGATION",
            urgency="P3_PROACTIVE",
            description="Review top talkers and cross-AZ data transfer traffic costs.",
            runbook_commands=[
                "aws ec2 describe-flow-logs --filter Name=traffic-type,Values=ALL",
            ],
            reasoning="Provides early visibility into rogue egress loops or inter-service payload serialization issues.",
            target_metric="Network",
        ))
        
    return actions


def evaluate_system_risk(metrics: Dict[str, MetricForecast]) -> SystemRiskReport:
    """Evaluate overall system risk level, dominant driver, and generate SRE runbook."""
    metric_risks: Dict[str, MetricRisk] = {}
    max_score = 1
    dominant_metric = "CPU"
    
    for key, forecast in metrics.items():
        risk = classify_metric_risk(forecast)
        metric_risks[key] = risk
        if risk.score > max_score:
            max_score = risk.score
            dominant_metric = forecast.display_name
            
    # Composite risk mapping
    score_to_level = {1: "LOW", 2: "MEDIUM", 3: "HIGH", 4: "CRITICAL"}
    overall_level = score_to_level[max_score]
    overall_color = RISK_COLORS[overall_level]
    
    # Generate headlines
    if overall_level == "CRITICAL":
        headline = f"CRITICAL ALERT: Capacity threshold breached or imminent on {dominant_metric}. Immediate action required."
    elif overall_level == "HIGH":
        headline = f"HIGH RISK: Rapid capacity exhaustion detected on {dominant_metric}. Breach projected shortly."
    elif overall_level == "MEDIUM":
        headline = f"ELEVATED RISK: Upward utilization trend observed. Plan proactive capacity scaling."
    else:
        headline = "NOMINAL: All infrastructure metrics operate within safe headroom parameters."
        
    # Gather operational actions
    all_immediate: List[OperationalAction] = []
    all_preventative: List[OperationalAction] = []
    
    for key, forecast in metrics.items():
        risk = metric_risks[key]
        if "cpu" in key:
            acts = build_cpu_recommendations(forecast, risk)
        elif "mem" in key:
            acts = build_memory_recommendations(forecast, risk)
        elif "net" in key:
            acts = build_network_recommendations(forecast, risk)
        else:
            acts = []
            
        for a in acts:
            if a.urgency in ["P1_IMMEDIATE", "P2_ELEVATED"]:
                all_immediate.append(a)
            else:
                all_preventative.append(a)
                
    # If system is healthy and no urgent actions, provide baseline health confirmation
    if not all_immediate and not all_preventative:
        all_preventative.append(OperationalAction(
            title="Maintain Baseline Monitoring & Normal Autoscaling Policies",
            category="SCALING",
            urgency="ROUTINE",
            description="System is operating within healthy parameters (< 60% utilization). No intervention required.",
            runbook_commands=[
                "# Verify cluster node health:",
                "kubectl get nodes",
                "kubectl top nodes",
            ],
            reasoning="All observed metric vectors indicate sufficient operational headroom.",
            target_metric="System",
        ))

    # Compile observed facts (strictly observational)
    observed_facts = []
    for key, forecast in metrics.items():
        observed_facts.append(
            f"Observed {forecast.display_name}: Current = {forecast.current_value:.1f}%, "
            f"Recent Avg = {forecast.recent_average:.1f}%, Linear Slope = {forecast.slope_per_hour:+.2f}%/h "
            f"(R²={forecast.r_squared:.2f})."
        )

    # Compile transparent rule reasoning
    rule_reasoning = []
    for key, risk in metric_risks.items():
        rule_reasoning.append(
            f"Risk Rule [{risk.level}] for {risk.display_name}: {risk.rationale}"
        )

    return SystemRiskReport(
        overall_level=overall_level,
        overall_color=overall_color,
        dominant_metric=dominant_metric,
        summary_headline=headline,
        metric_risks=metric_risks,
        immediate_actions=all_immediate,
        preventative_actions=all_preventative,
        observed_facts=observed_facts,
        rule_reasoning=rule_reasoning,
    )
