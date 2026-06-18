import pandas as pd

# Load your datasets
reading_df = pd.read_csv("reading.csv")
sensor_df = pd.read_csv("sensor_full.csv")

# Merge to associate sensor_id with sensor_type
merged_df = pd.merge(reading_df, sensor_df, on="sensor_id")

# Group by sensor type and calculate mean, std, and threshold
thresholds = (
    merged_df.groupby("sensor_type")["value"]
    .agg(["mean", "std"])
    .reset_index()
)

# Calculate threshold = mean + 3 * std
thresholds["threshold"] = thresholds["mean"] + 3 * thresholds["std"]

# Round for clarity
thresholds = thresholds[["sensor_type", "threshold"]].round(2)

# Print or export
print(thresholds)
