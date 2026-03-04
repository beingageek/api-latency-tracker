import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def generate_api_data(filename="api_logs.csv", num_records=15000):
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2026, 3, 1)
    delta_seconds = int((end_date - start_date).total_seconds())

    data = []
    apis = ["API 1", "API 2", "API 3", "API 4", "API 5"]

    print(f"Generating {num_records} records with seasonal and time-based logic...")

    for _ in range(num_records):
        # 1. Random Timestamp
        random_seconds = np.random.randint(0, delta_seconds)
        ts = start_date + timedelta(seconds=random_seconds)

        # 2. API Selection
        api_name = np.random.choice(apis)

        # Base latency parameters (Log-normal distribution)
        # mean is the log of the median; sigma is the spread
        mu, sigma = 7.0, 0.4  # API 1 baseline (~1100ms)

        if api_name == "API 2":
            mu, sigma = 7.2, 0.5  # API 2 baseline (~1300ms)
            # --- MORNING BOTTLENECK LOGIC ---
            # Increase latency by 80% if between 6 AM and 12 PM
            if 6 <= ts.hour < 12:
                mu += 0.6

        elif api_name == "API 3":
            mu, sigma = 8.5, 0.6  # API 3 baseline (~5000ms)

        # --- SEASONAL LOGIC (December Traffic) ---
        # If month is December, increase latency for ALL APIs by 50%
        if ts.month == 12:
            mu += 0.4

        # Generate duration
        duration = int(np.random.lognormal(mean=mu, sigma=sigma))

        # Format as the log string
        comment = f"{api_name} time taken millis = {duration}"
        data.append([ts.strftime('%Y-%m-%d %H:%M:%S'), comment])

    # Create DataFrame and sort
    df = pd.DataFrame(data, columns=['EventDate', 'EventComments'])
    df['EventDate'] = pd.to_datetime(df['EventDate'])
    df = df.sort_values('EventDate')

    df.to_csv(filename, index=False)
    print(f"File '{filename}' generated. Ready for analysis.")


if __name__ == "__main__":
    generate_api_data()