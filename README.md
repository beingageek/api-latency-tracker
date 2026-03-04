# Project Overview: API Latency Tracker

### The Mission

In modern software environments, APIs don't just "work" or "fail"—their performance fluctuates based on time of day, seasonal traffic, and infrastructure health.

The **API Latency Tracker** project provides a two-part solution to this challenge:

1. **The Generator:** Creates a "digital twin" of your API traffic, simulating 4 years of real-world behavior, including bottlenecks and holiday surges.
2. **The Visualizer:** Transforms raw, messy log strings into a high-definition, interactive dashboard that reveals long-term trends and hidden patterns.

---

### 1. The Core Philosophy

The project is built on three pillars of data science:

* **Long-Term Context:** By looking at a **4-year window**, we move past "yesterday's spike" and start seeing multi-year growth and degradation trends.
* **The "Long Tail" Reality:** We don't just track averages. By focusing on **Daily Maximums** and **Log-Normal distributions**, we highlight the rare but painful 60-second timeouts that frustrate users.
* **Dimensional Drilling:** Data is sliced by **API Type**, **Month-over-Month**, and **Intraday Windows** (6-hour blocks) to pinpoint exactly *when* and *where* a delay occurs.

---

### 2. How the Scripts Work Together

The following two steps form a complete testing and reporting loop:

1. **`Data Generator`:** It generates thousands of rows of data.
* It injects **"Synthetic Problems"** (like API 2 being slow every morning).
* **Goal:** To provide a rigorous test case for the visualizer.


2. **`Data Visualization`:**
* It cleans the data using Regex.
* It builds a standalone **HTML Dashboard**.
* **Goal:** To provide an executive-level view with engineer-level detail (drill-down).

The project offers two distinct visualization engines: **`api_chart_chartjs.py`**, which leverages the high-performance Chart.js library for web-native rendering, and **`api_chart_plotly.py`**, which utilizes Plotly for deep, scientific-grade interactivity. Each script provides a unique visual perspective and different chart layouts to suit various analytical needs.


---

### 3. Visualizer Feature Highlights

| Component | What it tells you |
| --- | --- |
| **Global Daily Median** | The "Pulse" of your entire API ecosystem over 4 years. |
| **YoY API Cards** | "Is API 1 slower this January than it was in 2024?" |
| **Intraday Facets** | "Do we have a capacity issue during the 6 AM morning rush?" |
| **Interactive Toggles** | The ability to "mute" everything except the specific API you are investigating. |
| **Dynamic Zoom/Pan** | The power to zoom from a 4-year overview down to a specific 48-hour incident. |

---

### 4. Summary of Benefits

* **Zero Infrastructure:** No database or server is required. Everything runs locally and exports to a portable HTML file you can email or Slack to teammates.
* **Pattern Recognition:** Easily spot "December Spikes" or "Morning Slumps" that are invisible in standard real-time monitoring tools.
* **Audit Ready:** The "Top 5 Slowest Calls" table gives you immediate targets for your next engineering sprint to improve system stability.

---

### 5. Project Origin & Credits

This entire suite—including the **Data Generator**, the **Data Visualizer**, and the accompanying documentation—was developed through a collaborative session with **Claude Code** and **Google Gemini**.

The project leverages cutting-edge AI logic to bridge the gap between raw unstructured logs and actionable business intelligence, ensuring that complex data engineering tasks are accessible, automated, and highly interactive.

---

### Project Summary

| Component | Function | Built With |
| --- | --- | --- |
| **Data Engine** | Statistical Log Generation | Python (NumPy, Pandas) |
| **Analysis** | Regex Extraction & Time-Series Aggregation | Python (Regex, Pandas) |
| **Visualization** | Interactive Web Dashboard | Plotly.js & Chart.js |
| **Interactivity** | Scroll-to-Zoom, Drag-to-Pan, Global Toggles | JavaScript (Plotly.js, Chart.js) |
