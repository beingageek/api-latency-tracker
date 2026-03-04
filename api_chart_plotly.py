import sys
import pandas as pd
import plotly.express as px
import re
from pathlib import Path

if len(sys.argv) < 2:
    print("Usage: python api_chart_plotly.py <path_to_csv> [output.html]")
    print("  <path_to_csv>  CSV with EventDate and EventComments columns")
    print("  [output.html]  Output file (default: api_report_gemini.html)")
    sys.exit(1)
csv_path    = Path(sys.argv[1])
output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("api_report_chart.html")

# 1. Load and Clean Data
df = pd.read_csv('api_logs.csv', parse_dates=['EventDate'])


def extract_info(text):
    api_match = re.search(r'(API \d+)', text)
    time_match = re.search(r'millis = (\d+)', text)
    return (api_match.group(1) if api_match else None,
            int(time_match.group(1)) if time_match else None)


df[['API_Type', 'Duration']] = df['EventComments'].apply(lambda x: pd.Series(extract_info(x)))
df = df.dropna(subset=['API_Type', 'Duration'])

# 2. Time Engineering
df['Date'] = df['EventDate'].dt.date
df['Month_Num'] = df['EventDate'].dt.month
df['Month_Name'] = df['EventDate'].dt.strftime('%b')
df['Year'] = df['EventDate'].dt.year.astype(str)
month_order = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def get_window(hour):
    if 0 <= hour < 6:
        return '00:00-06:00 (Night)'
    elif 6 <= hour < 12:
        return '06:00-12:00 (Morning)'
    elif 12 <= hour < 18:
        return '12:00-18:00 (Afternoon)'
    else:
        return '18:00-24:00 (Evening)'


df['Time_Window'] = df['EventDate'].dt.hour.apply(get_window)


# --- IMPROVED TOGGLE LOGIC ---
def add_api_dropdown(fig, df):
    """Fixed dropdown logic to handle multiple subplots and maintain consistent legends."""
    api_list = sorted(df['API_Type'].unique())
    buttons = []

    # "Show All" Button
    buttons.append(dict(
        method="update",
        label="Show All APIs",
        args=[{"visible": [True] * len(fig.data)}]
    ))

    # Individual API Buttons
    for api in api_list:
        # Match trace name to selected API to handle facets correctly
        visibility = [trace.name == api for trace in fig.data]
        buttons.append(dict(
            method="update",
            label=f"Only {api}",
            args=[{"visible": visibility}]
        ))

    fig.update_layout(
        updatemenus=[dict(
            buttons=buttons,
            direction="down",
            showactive=True,
            x=0.0, xanchor="left",
            y=1.25, yanchor="top"
        )]
    )
    return fig


# --- CHART GENERATION FUNCTIONS ---

def create_daily_chart(df, agg_func, title):
    # Sort for consistent color mapping
    df_sorted = df.sort_values('API_Type')
    daily = df_sorted.groupby(['Date', 'API_Type'])['Duration'].agg(agg_func).reset_index()

    fig = px.line(daily, x='Date', y='Duration', color='API_Type',
                  category_orders={"API_Type": sorted(df['API_Type'].unique())},
                  title=title)

    fig = add_api_dropdown(fig, df)

    # ENABLE SCROLL AND PAN
    fig.update_layout(dragmode='pan')  # Sets pan as default instead of box-select
    return fig.to_html(full_html=False, include_plotlyjs='cdn', config={'scrollZoom': True})  #


def create_window_chart(df):
    df_sorted = df.sort_values('API_Type')
    window_data = df_sorted.groupby(['Date', 'Time_Window', 'API_Type'])['Duration'].median().reset_index()

    fig = px.line(window_data, x='Date', y='Duration', color='API_Type',
                  facet_col='Time_Window', facet_col_wrap=2,
                  category_orders={"API_Type": sorted(df['API_Type'].unique())},
                  title="Daily Median by Time Windows")

    fig = add_api_dropdown(fig, df)
    fig.update_layout(dragmode='pan', legend_title_text='API Type')
    return fig.to_html(full_html=False, include_plotlyjs=False, config={'scrollZoom': True})


def create_api_specific_yoy(df):
    yoy_blocks = ""
    apis = sorted(df['API_Type'].unique())
    for api in apis:
        api_df = df[df['API_Type'] == api]
        api_yoy = api_df.groupby(['Year', 'Month_Name', 'Month_Num'])['Duration'].median().reset_index().sort_values(
            'Month_Num')
        fig = px.line(api_yoy, x='Month_Name', y='Duration', color='Year',
                      title=f"{api}: Year-over-Year History", markers=True,
                      category_orders={"Month_Name": month_order})
        fig.update_layout(dragmode='pan')
        yoy_blocks += f'<div class="api-card"><h3>{api}</h3>{fig.to_html(full_html=False, include_plotlyjs=False, config={"scrollZoom": True})}</div>'
    return yoy_blocks


# 3. Summary Table
slowest_days = df.groupby(['Date', 'API_Type'])['Duration'].max().reset_index()
slowest_days = slowest_days.sort_values('Duration', ascending=False).groupby('API_Type').head(5)
summary_table_html = slowest_days.to_html(classes='summary-table', index=False)

# --- CONSTRUCT HTML ---
html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>API Performance Report</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; margin: 40px; background-color: #f0f2f5; }}
        .section {{ background: white; padding: 25px; margin-bottom: 30px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }}
        .api-card {{ border-left: 5px solid #3498db; margin-top: 20px; padding: 10px; }}
        h1 {{ color: #2c3e50; text-align: center; }}
        .summary-table {{ width: 100%; border-collapse: collapse; font-size: 0.9em; }}
        .summary-table th, .summary-table td {{ padding: 10px; border: 1px solid #ddd; }}
        .summary-table th {{ background-color: #3498db; color: white; }}
    </style>
</head>
<body>
    <h1>API Performance Analysis (2023-2026)</h1>
    <p style="text-align:center;"><b>Interactivity Tip:</b> Use your mouse wheel to zoom. Click and drag to pan across the timeline.</p>

    <div class="section">
        <h2>Global Daily Trends</h2>
        {create_daily_chart(df, 'median', 'Median Latency Trends')}
    </div>

    <div class="section">
        <h2>Year-over-Year Trends by API</h2>
        {create_api_specific_yoy(df)}
    </div>

    <div class="section">
        <h2>Intraday Performance</h2>
        {create_window_chart(df)}
    </div>

    <div class="section">
        <h2>Top 5 Slowest Call Records per API</h2>
        {summary_table_html}
    </div>
</body>
</html>
"""

output_path.write_text(html_content, encoding="utf-8")
print(f"\n✅ Report saved: {output_path.resolve()}")