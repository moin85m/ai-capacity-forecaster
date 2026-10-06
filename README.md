# ⚡ AI Capacity Forecaster

> **A proactive Site Reliability Engineering (SRE) and Cloud Operations dashboard that analyzes resource utilization metrics, forecasts capacity threshold breaches, and generates automated scaling recommendations.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/framework-Streamlit-FF4B4B.svg)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Zero-Config Mode](https://img.shields.io/badge/Mode%20A-Offline%20%2F%20No--Key-brightgreen.svg)]()

---

## 📌 Executive Summary

Modern cloud infrastructure teams frequently experience **reactive firefighting** when CPU, Memory, or Network bandwidth saturate without warning. Traditional alerting triggers *after* a threshold is already breached.

**AI Capacity Forecaster** acts as an intelligent SRE cockpit:
1. **Monitors & Extrapolates**: Evaluates 24–48h time-series telemetry trends using explainable linear regression slopes.
2. **Predicts Threshold Breaches**: Computes exact estimated time-to-breach (e.g., *"CPU critical threshold projected in ~1h 32m"*).
3. **Assigns Risk Grades**: Transparently categorizes risk into `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL`.
4. **Prescribes Operational Remediation**: Recommends immediate `kubectl` / cloud autoscaling actions and long-term architectural tuning.
5. **Dual-Mode AI Architecture**:
   - **Mode A (Demo / Offline Mode)**: 100% deterministic heuristic rule engine; runs anywhere without requiring an API key.
   - **Mode B (AI-Assisted Mode)**: Optional integration with Google Gemini or OpenAI LLMs for incident synthesis and root-cause advisory.

---

## 🏗️ Architecture & Project Structure

```text
ai-capacity-forecaster/
│
├── app.py                      # Streamlit Operations Dashboard UI
├── requirements.txt            # Python dependencies
├── README.md                   # Technical documentation
├── PROJECT_SHOWCASE.md         # System design case study & architecture decisions
├── MY_INTERVIEW_PREP.md        # Personal interview prep & resume notes
├── .gitignore                  # Git ignore rules
│
├── data/
│   └── infrastructure_metrics.csv  # 48-hour hourly dummy telemetry dataset
│
├── src/
│   ├── __init__.py             # Package init
│   ├── forecasting.py          # Linear regression & time-to-threshold engine
│   ├── recommendations.py      # Transparent risk engine & operational runbooks
│   └── ai_advisor.py           # Dual-mode AI advisor (Local Heuristic vs LLM)
│
└── screenshots/
    └── .gitkeep                # UI screenshots directory
```

---

## 🧮 Forecasting & Risk Methodology

### 1. Explainable Linear Trend Regression
Rather than opaque "black-box" models, the forecaster uses least-squares linear regression over a configurable lookback window ($W \in [4, 24]$ hours):

$$\text{Slope } m = \frac{\sum (t - \bar{t})(y - \bar{y})}{\sum (t - \bar{t})^2} \quad (\%/\text{hour})$$

$$\text{ETA to Threshold } T = \frac{T - y_{\text{current}}}{m} \quad (\text{if } m > 0)$$

- **Imminent Warning**: If $m \le 0$, system confirms: *"No threshold breach projected (trend is stable or decreasing)"*.
- **Confidence Metric**: Calculates $R^2$ to report goodness-of-fit for operational transparency.

### 2. Transparent Risk Matrix

| Risk Level | Trigger Conditions | Operational Posture |
|---|---|---|
| **CRITICAL** | Utilization $\ge 90\%$ OR critical breach projected in $\le 1.0$ hour | **P1 Emergency**: Trigger instant horizontal pod scale-out or manual node intervention. |
| **HIGH** | Utilization $\ge 75\%$ OR critical breach projected in $\le 2.5$ hours | **P2 Elevated**: Increase autoscaling targets and verify compute headroom. |
| **MEDIUM** | Utilization $60\% - 75\%$ with positive slope OR breach in $\le 6$ hours | **P3 Proactive**: Review capacity headroom, cache hit rates, and garbage collection. |
| **LOW** | Utilization $< 60\%$ with stable/negative slope | **Nominal**: Standard baseline monitoring. |

---

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.11+ (or WSL 2 / Ubuntu / macOS)
- Standard web browser

### 1. Clone & Enter Directory
```bash
git clone <your-repo-url>
cd "ai-capacity-forecaster"
```

### 2. Create Virtual Environment & Install Dependencies
```bash
# On Linux / WSL / macOS:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# On Windows (PowerShell):
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Launch Dashboard
```bash
streamlit run app.py
```
The application will launch immediately at `http://localhost:8501`.

---

## 🔑 Mode Configuration (Offline vs LLM)

- **Mode A (Default - No Setup Required)**:
  Works straight out of the box with zero credentials or internet access.
- **Mode B (Optional LLM Integration)**:
  Set your environment variable or input your key directly into the sidebar:
  ```bash
  export GEMINI_API_KEY="your-gemini-key"
  # or
  export OPENAI_API_KEY="your-openai-key"
  ```

---

## 📊 Workload Simulation Scenarios

The dashboard includes built-in interactive scenario generators in the sidebar:
1. **Default (48h Workload Growth)**: Simulates steady business growth leading toward saturation.
2. **Memory Leak Simulation**: Constant compute load with monotonic memory escalation.
3. **Sudden Traffic Spike**: Flat telemetry followed by an exponential surge in requests.
4. **Stable / Healthy State**: Balanced baseline operations.
5. **Custom CSV Upload**: Bring your own infrastructure monitoring data.

---

## 🛡️ Security & Privacy
- **Self-Generated Data**: Uses 100% synthetic dummy infrastructure metrics. No proprietary or personal data is collected or transmitted.
- **Credential Protection**: API keys are handled strictly in memory and are never written to disk or logs.
