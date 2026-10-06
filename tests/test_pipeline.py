import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
from src.forecasting import analyze_all_metrics
from src.recommendations import evaluate_system_risk
from src.ai_advisor import run_offline_advisory

def run_tests():
    print("Testing data loading...")
    df = pd.read_csv("data/infrastructure_metrics.csv")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    assert len(df) == 48, f"Expected 48 rows, got {len(df)}"
    print(f"Loaded {len(df)} telemetry rows.")

    print("\nTesting forecasting engine...")
    metrics = analyze_all_metrics(
        df=df,
        lookback_points=12,
        warning_threshold=75.0,
        critical_threshold=90.0,
    )
    assert "cpu_percent" in metrics
    assert "memory_percent" in metrics
    assert "network_percent" in metrics
    for k, v in metrics.items():
        print(f"  [{k}] Current: {v.current_value:.1f}%, Slope: {v.slope_per_hour:+.2f}%/h, Critical ETA: {v.critical_eta_text}")

    print("\nTesting risk classification and operational recommendations...")
    risk = evaluate_system_risk(metrics)
    print(f"  Overall System Risk: {risk.overall_level} (Dominant: {risk.dominant_metric})")
    assert risk.overall_level in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    print(f"  Immediate Actions: {len(risk.immediate_actions)}")
    print(f"  Preventative Actions: {len(risk.preventative_actions)}")

    print("\nTesting Mode A Offline SRE Advisor...")
    advisor = run_offline_advisory(metrics, risk)
    assert advisor.mode == "Mode A (Demo / Offline Mode)"
    print(f"  Advisory Mode: {advisor.mode}")
    print(f"  Advisory Provider: {advisor.provider}")
    print(f"  Capacity Summary: {advisor.capacity_interpretation[:100]}...")
    print("\nALL SMOKE TESTS PASSED SUCCESSFULLY! ✅")

if __name__ == "__main__":
    run_tests()
