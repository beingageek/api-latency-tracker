# Documentation: API Performance Visualizer using Chart.js

**File:** `api_chart_claude.py`  
**Output:** A single self-contained `.html` file with interactive charts  
**Python version:** 3.8+

> **Note:** This script was created using [Claude Code](https://claude.ai/code), Anthropic's agentic coding tool.

---

## Overview

`api_chart_claude.py` is a Python script that reads a CSV log file containing API event records, aggregates the data across several time dimensions, and produces a **single self-contained HTML file** with fully interactive charts. The output file has no external dependencies beyond a CDN connection for JavaScript libraries — it can be opened directly in any modern browser without a web server.

The report covers six chart views:

| # | View | Grouping |
|---|------|----------|
| 1 | Daily Median response time | Per API type |
| 2 | Daily Minimum response time | Per API type |
| 3 | Daily Maximum response time | Per API type |
| 4 | Monthly Median response time | Per API type |
| 5 | Year-over-Year same-month comparison | Per API type (tabbed) |
| 6 | Daily Median by 6-hour time frame | Per time frame (tabbed), all APIs |

A **global API filter bar** allows toggling individual API types on or off across all charts simultaneously.

---

## Setup & Usage

### Installation

```bash
pip install pandas
```

### Running

```bash
python api_chart_claude.py <path_to_csv>
# Output: api_report_plotly.html (same directory)

python api_chart_claude.py <path_to_csv> my_report.html
# Output: my_report.html at the specified path
```

### Example

```bash
python api_chart_claude.py logs/api_logs.csv reports/performance.html
```

The script prints a summary to stdout as it runs:

```
📂 Loading: api_events.csv
   12,847 records  |  APIs: ['API 1', 'API 2', 'API 3']
   Range: 2023-01-01 → 2026-03-01

⚙️  Building report data …

✅ Report saved: /home/user/reports/performance.html
   Open in any browser — fully self-contained, no server needed.
```

---

## Input Format

The script expects a CSV file with at minimum these two columns:

| Column | Type | Description |
|--------|------|-------------|
| `EventDate` | Datetime string | Timestamp of the API call. Any format parseable by `pandas.to_datetime` is accepted (e.g. `2026-03-03 13:14:10`). |
| `EventComments` | String | Free-text comment containing the API name and duration. Must match the pattern described below. |

### EventComments Pattern

The script extracts the API name and duration using this regular expression (case-insensitive):

```
(API\s+\d+)\s+time taken millis\s*=\s*(\d+)
```

**Valid examples:**

```
API 1 time taken millis = 3520
API 2 time taken millis=2100
api 3 Time Taken Millis = 59000
```

Rows where `EventComments` does not match this pattern, or where `EventDate` cannot be parsed, are silently dropped.

### Sample CSV

```csv
EventDate,EventComments
2026-03-03 13:14:10,API 1 time taken millis = 3520
2026-03-03 13:14:52,API 2 time taken millis = 2100
2026-03-03 14:09:00,API 3 time taken millis = 59000
```

Extra columns in the CSV are ignored. Column names are whitespace-stripped before matching, so `" EventDate "` is treated the same as `"EventDate"`.

---

## Python Libraries

### Standard Library (no installation needed)

| Module | Usage |
|--------|-------|
| `json` | Serialises aggregated data into JSON that is embedded directly inside the HTML template. |
| `re` | Compiles the regex pattern used to extract API name and millisecond value from `EventComments`. |
| `sys` | Reads command-line arguments (`sys.argv`) and exits with an error code on bad input. |
| `datetime` | Formats the report generation timestamp inserted into the HTML header. |
| `pathlib.Path` | Cross-platform file path handling for reading the input CSV and writing the output HTML. |

### Third-Party (requires installation)

#### `pandas` (`pip install pandas`)

The only third-party dependency. Used throughout the data pipeline:

| Feature | How it's used |
|---------|---------------|
| `pd.read_csv` | Loads the input CSV into a DataFrame. |
| `pd.to_datetime` | Parses `EventDate` strings into proper datetime objects; invalid values become `NaT` and are dropped. |
| `Series.str.extract` | Applies the regex pattern across the entire `EventComments` column in one vectorised operation to extract API name and millisecond value. |
| `DataFrame.groupby` + `.agg` | Computes median, min, and max response times grouped by date and API type. |
| `DataFrame.unstack` | Pivots the grouped result so each API type becomes its own column — the format Chart.js expects. |
| `pd.Period` / `.to_timestamp` | Handles month-level grouping with proper calendar-month semantics. |
| `pd.date_range` | Generates a complete daily date spine from the dataset's first to last date, ensuring all time-frame series have identical x-axis labels and no artificial gaps. |
| `DataFrame.reindex` | Aligns all series to the shared date spine, filling missing days with `NaN` (which becomes `null` in JSON, handled gracefully by Chart.js). |

---

## JavaScript Libraries (embedded in output)

All JavaScript libraries are loaded from the **cdnjs.cloudflare.com** CDN. The output HTML file requires an internet connection to load these scripts; once loaded, the page runs entirely client-side.

### Chart.js `v4.4.1`

**CDN:** `https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js`

The primary charting library. All six chart views are rendered as **line charts** (`type: 'line'`). Key Chart.js features used:

| Feature | Purpose |
|---------|---------|
| `responsive: true` | Charts resize automatically when the browser window is resized. |
| `maintainAspectRatio: false` | Allows explicit height control via the CSS wrapper `div`. |
| `interaction.mode: 'index'` | Tooltip shows all API values at the hovered x-position simultaneously. |
| `spanGaps` | Set to `true` on time-frame charts (bridges over days with no data) and `false` on daily/monthly/YoY charts (breaks lines at true data gaps). |
| `dataset.hidden` | Toggled programmatically by the API filter bar to show/hide individual API lines. |
| `chart.update('none')` | Re-renders charts instantly without animation when the filter state changes. |

### Hammer.js `v2.0.8`

**CDN:** `https://cdnjs.cloudflare.com/ajax/libs/hammer.js/2.0.8/hammer.min.js`

A touch gesture library required by `chartjs-plugin-zoom` to support pinch-to-zoom on mobile and tablet devices. Has no direct API usage in the script — it is a peer dependency.

### chartjs-plugin-zoom `v2.0.1`

**CDN:** `https://cdnjs.cloudflare.com/ajax/libs/chartjs-plugin-zoom/2.0.1/chartjs-plugin-zoom.min.js`

Adds interactive zoom and pan to charts that support it. Configured per chart:

| Setting | Value | Effect |
|---------|-------|--------|
| `zoom.wheel.enabled` | `true` | Scroll wheel zooms the x-axis. |
| `zoom.pinch.enabled` | `true` | Pinch gesture zooms on touch devices. |
| `pan.enabled` | `true` | Click-and-drag pans horizontally. |
| `mode` | `'x'` | Zoom and pan are restricted to the time axis only. |

Zoom is **enabled** on: Daily Stats (all three), Time Frames.  
Zoom is **disabled** on: Monthly Median, Year-over-Year (the x-axis is fixed month labels, not a continuous time scale).

A **double-click** on any zoomable chart resets the zoom to the full view.

### Google Fonts

**URL:** `https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Syne:wght@700;800&display=swap`

Two typefaces are loaded for the report UI:

- **DM Mono** — used for all body text, labels, tooltips, and axis ticks. A monospaced font that suits a technical/data dashboard aesthetic.
- **Syne** — used for large headings, section titles, and the metric values in the summary bar.

---

## Overall Flow

The script follows a linear pipeline from raw CSV to finished HTML:

```
CSV file
   │
   ▼
1. load_data()
   Parse dates, extract API name + millis via regex,
   derive date/month/year/hour/timeframe columns.
   │
   ▼
2. Colour assignment (main)
   Sort unique API names alphabetically, assign
   each a hex colour from API_PALETTE in order.
   │
   ▼
3. build_json()
   Call all aggregation helpers and assemble
   a single Python dict with all chart data.
   │
   ├── daily_pivot(df, "median") ──► pivot_to_chartjs()
   ├── daily_pivot(df, "min")    ──► pivot_to_chartjs()
   ├── daily_pivot(df, "max")    ──► pivot_to_chartjs()
   ├── monthly_pivot(df)         ──► monthly_to_chartjs()
   ├── yoy_data(df)              ──► raw dict {api: {year: [12 values]}}
   └── timeframe_data(df)        ──► raw dict {timeframe: {api: {labels, values}}}
   │
   ▼
4. json.dumps(payload)
   Serialise the entire data dict to a JSON string.
   NaN values from pandas become JSON null automatically.
   │
   ▼
5. HTML template substitution (main)
   Replace __PLACEHOLDER__ tokens in the HTML string
   with runtime values (dates, record counts, JSON data).
   │
   ▼
6. output_path.write_text()
   Write the final HTML string to disk as UTF-8.
```

### Template Substitution Tokens

The HTML template contains placeholder strings replaced at the end of `main()`:

| Token | Replaced with |
|-------|--------------|
| `__GENERATED_AT__` | Current date and time (`YYYY-MM-DD HH:MM`) |
| `__SOURCE__` | Input CSV filename (basename only) |
| `__RECORDS__` | Total number of valid records parsed, formatted with commas |
| `__APIS__` | Count of distinct API types found |
| `__RANGE__` | First and last month in the dataset (e.g. `Jan 2023 – Mar 2026`) |
| `__SPAN__` | Human-readable data span (e.g. `3y 2m` or `45d`) |
| `__JSON_DATA__` | Full JSON payload of all chart data |
| `__TF_COLORS__` | JSON object mapping time frame names to hex colours |
| `__TF_ORDER__` | JSON array defining the canonical time frame order |

---

## Module Reference

### `load_data(filepath) → pd.DataFrame`

Reads the CSV, parses all date/time fields, extracts API type and millisecond values via regex, and appends derived columns. Rows with unparseable dates or non-matching comments are silently dropped.

**Derived columns added:**

| Column | Type | Description |
|--------|------|-------------|
| `api_type` | str | Extracted API name, e.g. `"API 1"` |
| `millis` | float | Response time in milliseconds |
| `date` | date | Calendar date (no time component) |
| `month` | Period | Year-month period for monthly grouping |
| `month_num` | int | Month number 1–12 for YoY alignment |
| `year` | int | Calendar year |
| `hour` | int | Hour of day 0–23 |
| `timeframe` | str | One of four 6-hour bucket labels |

### `daily_pivot(df, stat) → pd.DataFrame`

Groups records by `(date, api_type)`, applies the given aggregation (`"median"`, `"min"`, or `"max"`), and returns a pivot table where the index is a DatetimeIndex and each column is one API type.

### `monthly_pivot(df) → pd.DataFrame`

Groups records by `(month, api_type)`, computes the median, and returns a pivot table with a DatetimeIndex (month start dates) and one column per API type.

### `yoy_data(df) → (dict, list)`

Returns a nested dict `{api_name: {year: [v_jan, v_feb, ..., v_dec]}}` where each list has exactly 12 entries (one per month), with `None` for months that have no data. Also returns a sorted list of all years present in the dataset.

### `timeframe_data(df) → dict`

Returns `{timeframe: {api_name: {labels: [...], values: [...]}}}`. All series for a given time frame share the **same date labels list** (a continuous daily spine from dataset start to end), so Chart.js can render all API lines on a common x-axis. Missing days are `None` (rendered as gaps when `spanGaps: false`, bridged when `spanGaps: true`).

### `pivot_to_chartjs(pivot, api_colors) → dict`

Converts a pivot DataFrame (date index, API columns) into a Chart.js-compatible `{labels, datasets}` dict for daily charts. Date labels are formatted as `YYYY-MM-DD`. Point radius is small (`1px`) to reduce clutter on dense multi-year daily series.

### `monthly_to_chartjs(pivot, api_colors) → dict`

Same as `pivot_to_chartjs` but formats labels as `"Mon YYYY"` (e.g. `"Jan 2024"`) and uses larger point markers (`4px`) appropriate for the coarser monthly granularity.

### `build_json(df, api_colors) → dict`

Orchestrates all aggregation helpers and assembles the master data payload that gets embedded in the HTML. This is the single dict passed to `json.dumps`.

### `main()`

Entry point. Validates arguments, calls `load_data`, assigns colours, calls `build_json`, performs template substitution, and writes the output file.

---

## Output Report — Charts & Features

### Navigation

The report has four top-level tabs in a persistent navigation bar:

- **Daily Stats** — three charts (Median, Min, Max), all APIs as coloured lines over time
- **Monthly Median** — one chart with monthly aggregation
- **Year-over-Year** — sub-tabbed by API, each chart overlays all years on a Jan–Dec axis
- **Time Frames** — sub-tabbed by time window, each chart shows all APIs for that window

### API Filter Bar

A sticky bar sits below the navigation and remains visible while scrolling. It contains:

- **One toggle button per API**, showing the API's colour dot. Click to hide or show that API across all charts.
- **Show all** — instantly restores all APIs.
- **Hide all** — hides all APIs (useful as a starting point for isolating one API by then clicking it on).

The filter works by setting `dataset.hidden` on every registered Chart.js instance and calling `chart.update('none')` (no animation) to apply the change instantly. Charts that have not yet been rendered (lazy-built tabs) also pick up the current filter state at their first render.

### Zoom & Pan (Daily Stats and Time Frames)

- **Scroll wheel**: zooms in/out on the time axis
- **Click and drag**: pans left or right
- **Pinch** (touch devices): zooms in/out
- **Double-click**: resets zoom to the full view

### Lazy Chart Rendering

Year-over-Year and Time Frame charts are built only when their tab is first visited. This keeps the initial page load fast regardless of how many API types are in the dataset. A `data-built` attribute on each card prevents duplicate chart instances.

An important detail for YoY charts: the card is made **visible before** the Chart.js instance is created. This ensures the canvas element has a non-zero measured width when Chart.js initialises, which is required for correct responsive sizing.

### Tooltips

All charts use a unified tooltip style (dark background, all series at the current x-position shown together) with values formatted as:
- Milliseconds below 1000: `ms` suffix (e.g. `842ms`)
- Milliseconds 1000 and above: converted to seconds with two decimal places (e.g. `1.34s`)

---

## Configuration & Customisation

### Adding More API Types

No changes are needed. API types are detected dynamically from the `EventComments` column. Up to 12 APIs will receive distinct colours from `API_PALETTE`; beyond 12 the palette cycles.

### Changing API Colours

Edit the `API_PALETTE` list near the top of the script. Colours are assigned to API types in sorted alphabetical order:

```python
API_PALETTE = [
    "#00e5ff",  # API 1
    "#69ff6e",  # API 2
    "#ffb347",  # API 3
    # ... up to 12 entries before cycling
]
```

### Changing Time Frame Colours

Edit the `TF_COLORS` dict:

```python
TF_COLORS = {
    "12AM-6AM": "#7c4dff",
    "6AM-12PM": "#00bcd4",
    "12PM-6PM": "#ff9800",
    "6PM-12AM": "#e91e63",
}
```

### Changing Time Frame Boundaries

Edit the `bucket()` function inside `load_data()` and update both `TF_COLORS` and `TIMEFRAMES` to match:

```python
def bucket(h):
    if   0 <= h <  6: return "12AM-6AM"
    elif 6 <= h < 12: return "6AM-12PM"
    elif 12 <= h < 18: return "12PM-6PM"
    else:              return "6PM-12AM"
```

### Changing the Default Output Filename

Pass a second argument on the command line, or edit the fallback in `main()`:

```python
output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("api_report.html")
```

---

## Design Decisions & Known Behaviours

### Self-contained output

All aggregated data is embedded directly in the HTML as an inline JSON object. The output file does not reference the original CSV, does not write any auxiliary files, and does not require Python to view — just a browser.

### Why `spanGaps: true` on time-frame charts

Days where an API had no calls in a specific 6-hour window produce `null` values. With `spanGaps: false`, Chart.js breaks the line at every null, making the chart look fragmented even when the API was active most days. Setting `spanGaps: true` bridges over these nulls, resulting in a continuous line that accurately reflects overall trends while still showing genuine data-free periods as slight visual irregularities in the tooltip.

### Shared date spine for time-frame data

Each time-frame series is reindexed to a single complete daily date range (`pd.date_range` from min to max date). This ensures all series have identical label arrays, which is a requirement for Chart.js to correctly align multiple datasets on a shared x-axis. Without this, series with different date sets would be misaligned.

### Colour palette scope

`API_PALETTE` assigns colours only to API types (used across all chart views). The time-frame colours in `TF_COLORS` are a separate palette used only internally for the filter bar legend on the Time Frames tab — the time-frame charts themselves display API colours, not time-frame colours, because each chart shows all APIs.

### Record count vs. row count

The "Records" figure in the report header reflects the number of rows that **successfully parsed** — those with a valid `EventDate` and a matching `EventComments` pattern. Malformed or unrecognised rows are excluded silently.