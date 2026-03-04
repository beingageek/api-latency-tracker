# Documentation: API Log Data Generator

This documentation covers the Python utility script used to create synthetic, high-fidelity API event logs for testing and benchmarking the visualization suite.

---

### 1. Technical Stack

The generator is designed for speed and statistical realism, ensuring that the resulting charts reflect actual system behavior rather than flat, linear data.

#### **Python Libraries**

* **Pandas:** Used to structure the generated data into a DataFrame and export it to a standardized CSV format.
* **NumPy:** The core engine for "vectorized" random number generation. It provides the **Log-Normal distribution** functions used to simulate realistic latency spikes.
* **DateTime/TimeDelta:** Used to calculate the temporal range from 2023 to 2026 and distribute random events across that span.

---

### 2. Statistical Logic & Realism

Unlike a simple random generator, this script implements specific "hidden" behaviors to test the analytical capabilities of the visualizer:

#### **Log-Normal Latency**

In real-world systems, API response times are not a "Bell Curve" (Normal Distribution). Most calls are fast, but "long-tail" events (garbage collection, network blips) cause massive spikes.

* The script uses `np.random.lognormal` to ensure the **Median** stays low while the **Maximum** occasionally hits very high values.

#### **Behavioral Rules (The "Test Patterns")**

To verify that the charts are working, the following logic is hard-coded into the generator:

* **API Differentiation:** API 3 is intentionally set with a higher base latency (~5000ms) than API 1 (~1100ms) to test color-coding and stacking.
* **Seasonal Load:** Any record generated in **December** receives a **50% latency penalty** to simulate holiday traffic spikes.
* **Time-of-Day Bottleneck:** **API 2** is programmed to be **80% slower** specifically between **6:00 AM and 12:00 PM**, testing the "Intraday Performance" facets.

---

### 3. Script Workflow

1. **Range Calculation:** The script determines the total number of seconds between `2023-01-01` and `2026-03-01`.
2. **Random Sampling:** For every record (default 15,000):
* A random second within that range is chosen to create a `Timestamp`.
* An API name is randomly assigned.


3. **Contextual Scaling:** The script checks the `Month` and `Hour` of the timestamp to apply the Seasonal or Morning penalties described above.
4. **String Formatting:** The data is converted into the specific string format required by the visualizer: `API X time taken millis = N`.
5. **Sorting:** The final dataset is sorted chronologically before being saved to `api_logs.csv` to ensure compatibility with time-series tools.

---

### 4. Configuration

You can modify the following variables at the top of the `generate_api_data` function:

| Variable | Description |
| --- | --- |
| `num_records` | Increase this (e.g., to 50,000) to see denser trends and more outliers. |
| `mu` / `sigma` | Adjust these to change the average speed and "volatility" of an API. |
| `start_date` / `end_date` | Change these to test different year-over-year spans. |

---

### 5. Execution

Run the script via your terminal:

```bash
python api_gen.py

```

Upon completion, it will generate a file named `api_logs.csv`. You can then run the **Visualizer Script** to see these generated patterns come to life in the HTML report.
