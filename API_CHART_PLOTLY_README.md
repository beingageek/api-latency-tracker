# Documentation: API Performance Visualizer using Plotly.js

**File:** `api_chart_plotly.py`  
**Output:** A single self-contained `.html` file with interactive charts  
**Python version:** 3.8+

> **Note:** This script was created using [Google Gemini](https://gemini.google.com/), Google's AI coding tool.

---

## Technical Stack

The solution utilizes a hybrid approach, using Python for heavy data processing and JavaScript for client-side interactivity.

#### **Python Libraries**

* **Pandas:** The core engine for data manipulation. It handles CSV parsing, date-time conversion, and complex "group-by" aggregations.
* **Plotly (plotly.express):** A high-level visualization library used to generate the charts. It produces JSON-serialized data that is embedded into the HTML.
* **Regular Expressions (`re`):** Used to parse the unstructured `EventComments` string to extract specific API names and numerical millisecond values.

#### **JavaScript Libraries**

* **Plotly.js:** The report automatically fetches this via CDN (`include_plotlyjs='cdn'`). This library is what makes the charts interactive (hover, zoom, pan, and API toggling) without needing a Python server running in the background.

---

## Data Flow & Logic

The script follows a linear pipeline to transform raw logs into a structured dashboard:

1. **Ingestion & Extraction:** * The script reads `EventDate` and `EventComments`.
* It applies a Regex pattern: `(API \d+)` to find the API name and `millis = (\d+)` to capture the duration.


2. **Feature Engineering:**
* **Time Binning:** Hours are mapped into 6-hour quadrants (Night, Morning, Afternoon, Evening).
* **Date Normalization:** Dates are broken into `Year`, `Month_Name`, and `Month_Num` to facilitate chronological sorting.


3. **Aggregation:**
* The script calculates **Median**, **Minimum**, and **Maximum** values per day and per month.
* For the Year-over-Year (YoY) section, it isolates data for each API and groups it by year and month.


4. **Interactive Layer Injection:**
* Custom dropdown menus are injected into the Plotly objects to allow global API filtering.
* Config settings are applied to enable `scrollZoom` and default `dragmode='pan'`.


5. **HTML Synthesis:**
* The script uses Python f-strings to inject CSS styles, the Summary Table (as a standard HTML table), and the Chart components into a single `.html` file.



---

## Key Interactivity Features

| Feature | Action |
| --- | --- |
| **Global Toggle** | Use the "Only API X" dropdown to isolate a single service across faceted charts. |
| **Chronological YoY** | Charts are forced to display Jan–Dec order, even if some months are missing data. |
| **Zoom/Pan** | Scroll with the mouse wheel to zoom into a specific date. Click and drag to pan left/right. |
| **Reset View** | Double-click anywhere on a chart to return to the default 4-year view. |
| **Legend Isolation** | Click an API name in the legend to toggle it off; double-click a name to isolate it. |

---

## Setup & Usage

### Installation

```bash
pip install pandas plotly
```

### Running

```bash
python api_chart_plotly.py <path_to_csv>
# Output: api_report_plotly.html (same directory)

python api_chart_plotly.py <path_to_csv> my_report.html
# Output: my_report.html at the specified path
```

### Example

```bash
python api_chart_plotly.py logs/api_logs.csv reports/performance.html
```

> **Note on Performance:** For datasets exceeding 100,000 records, the HTML file size may increase significantly. In such cases, consider resampling the data to hourly medians within the Python script before passing it to the visualization functions.
