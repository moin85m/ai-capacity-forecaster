# 🎯 Candidate Interview Prep & Personal Reference Guide

> **Note**: This file is your personal reference guide for job applications, interview preparation, and LinkedIn sharing. Keep this for your own review!

---

## 📋 Copy-Paste Resume Bullet Points

### For Site Reliability Engineering (SRE) Roles:
> • **Architected and developed "AI Capacity Forecaster"**, an automated infrastructure operations dashboard utilizing Python, Streamlit, and Plotly to predict compute, memory, and network saturation up to 12 hours in advance.  
> • **Engineered an explainable time-series trend forecasting engine** with configurable lookback windows and $R^2$ confidence scoring, replacing reactive alarms with proactive time-to-breach estimations.  
> • **Implemented a hybrid deterministic-and-Generative AI advisory system** (Google Gemini / OpenAI), automating incident triage, risk classification, and step-by-step `kubectl` / AWS CLI autoscaling runbooks.

### For Cloud / DevOps Engineer Roles:
> • **Designed an AI-assisted cloud capacity forecasting prototype** in Python, analyzing 48-hour multi-metric telemetry (CPU, RAM, Bandwidth, Ingress RPS) to automate cluster autoscaling decisions.  
> • **Built transparent 4-tier risk classification logic** (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), correlating ingress request spikes with pod replica counts to prevent Out-Of-Memory (OOM) and compute saturation.  
> • **Created a zero-dependency offline fallback mode** alongside LLM-driven incident analysis, ensuring uninterrupted operational guidance in air-gapped or restricted cloud environments.

### For Platform / Infrastructure Engineering Roles:
> • **Developed an intelligent infrastructure capacity predictor** leveraging least-squares regression slopes to calculate exact time-to-threshold breaches across Kubernetes nodes and microservices.  
> • **Delivered interactive telemetry dashboards** with Plotly, providing real-time trend trajectories, threshold projection bands, and one-click synthetic failure scenario simulations (memory leaks, traffic surges).  
> • **Standardized incident response runbooks** with automated command generation, reducing Mean Time to Resolution (MTTR) and eliminating capacity firefighting.

---

## 🎙️ 30-Second Interview Elevator Pitch

> *"In high-scale infrastructure, most teams are notified of capacity problems reactively—after a node is already saturated or an OOM-kill has happened. I built the **AI Capacity Forecaster** to solve that. It monitors live compute, memory, and network telemetry, computes explainable linear growth slopes, and predicts exactly when thresholds will be breached hours in advance. It features a transparent 4-tier risk engine, generates immediate `kubectl` scaling runbooks, and uses a dual-mode pattern: a 100% offline rule engine for air-gapped resilience, plus an optional LLM advisor for incident narrative synthesis."*

---

## ❓ Anticipated Technical Questions & Strong Answers

### Q1: "Why did you use linear regression instead of an LSTM, Prophet, or transformer model?"
> **Answer**:  
> *"In production SRE operations, trust and explainability are paramount. When an on-call engineer is deciding whether to scale up 20 nodes, they need defensible math they can calculate in their head: `(90% - current) / slope = ETA`. Deep learning models on noisy 24-48h telemetry tend to overfit to short-term spikes or hallucinate seasonality. Linear regression provides sub-millisecond in-memory execution, zero GPU dependencies, and reliable short-term extrapolation."*

### Q2: "What happens if the LLM API is down or throttled during an outage?"
> **Answer**:  
> *"That's why I designed a dual-mode architecture. Mode A is completely offline and deterministic—it requires zero API keys and relies on local heuristic rule trees. It can run in an air-gapped VPC or during a cloud network partition. Mode B is strictly an optional layer that enhances the report with narrative synthesis and architecture advice when keys are present."*

### Q3: "How do you avoid alert fatigue or false alarms?"
> **Answer**:  
> *"The system uses a configurable lookback window (defaulting to 12 hours) and computes an $R^2$ goodness-of-fit score. If the slope is negative or flat, the system explicitly confirms that no breach is projected. Furthermore, the risk engine requires sustained positive growth before escalating to High or Critical."*

---

## 🌐 LinkedIn / GitHub Post Template

```text
🚀 Excited to share my latest cloud engineering project: AI Capacity Forecaster!

In cloud-native infrastructure, reactive alarms often mean you're already in the middle of a customer-impacting outage. I built AI Capacity Forecaster to show how proactive trend modeling and AI can assist SRE and platform teams in preventing capacity breaches before they happen.

Key Highlights:
🔹 Proactive Saturation Projections: Extrapolates multi-vector telemetry (CPU, RAM, Network) to calculate time-to-breach hours in advance.
🔹 Transparent Risk Scoring: Replaces black-box alerts with explainable math (R² confidence) and 4-tier risk states.
🔹 Actionable SRE Runbooks: Generates executable horizontal/vertical scaling commands (kubectl, AWS ASG).
🔹 Dual-Mode Reliability: Works 100% offline via local heuristics, with optional LLM integration for root-cause synthesis.

Tech Stack: Python, Streamlit, Pandas, NumPy, Plotly, Google Gemini API, OpenAI API.

🔗 Code & Case Study: https://github.com/moin85m/ai-capacity-forecaster
```
