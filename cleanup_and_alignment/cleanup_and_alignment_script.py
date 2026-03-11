# ------------------------------------------------------
# Clean up and alignment of the datasets
# ------------------------------------------------------
from .time_matching import time_match_radars, remove_downtime_intervals_from_ds
from .height_slicing import slice_height_range
from .range_gate_resolution import calculate_range_gate_resolution

# Set the arrays for storing results
combined_downtime = []
combined_uptime = []
combined_assumed_starting_seconds = 0
combined_longer_than_30_seconds_counts = 0


def cleanup_and_align_datasets(data, params):
    # ---------------------
    # Time matching radars
    # ---------------------
    print("⏱️ Time-matching radars based on uptime...")
    uptime_results = time_match_radars(data, params)
    print("⏱️ ✅ Time-matching completed. Uptime results calculated for all radars.")

    # ---------------------
    # Height slicing
    # ---------------------
    print("🗼 Height slicing...")
    data, highest_minimum_height, lowest_maximum_height = slice_height_range(data, params)
    print("🗼 ✅ Height slicing completed.")

    # -------------------------------------------------------
    # RANGE GATE RESOLUTION
    # -------------------------------------------------------
    print("📏 Calculating range gate resolution and adding it to the datasets...")
    data, unique_range_gate_sizes = calculate_range_gate_resolution(data, params)
    print("📏 ✅ Range gate resolution calculated.")

    # -------------------------------------------------------
    # Cleaning
    # -------------------------------------------------------
    print("🧹 Removing downtime intervals from the datasets...")
    data = remove_downtime_intervals_from_ds(data, params, highest_minimum_height, lowest_maximum_height, unique_range_gate_sizes, uptime_results)
    print("🧹 ✅ Downtime intervals removed from the datasets.")

    return data
    