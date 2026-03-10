# --------- MAIN SCRIPT ---------

# Import necessary modules
import xarray as xr
import json

from config import get_days_in_time_range

xr.set_options(use_new_combine_kwarg_defaults=True) # Setting the data_vars = 'None' as default and not 'all'

print("\n\n--------- 1) Loading configuration files ---------")
from config import load_radar_settings, load_dataset_settings
# Load radar settings and create RadarSettings objects for each radar
radar_settings_dict = load_radar_settings("config/radar_settings.json")
print(f"✅ Radar settings loaded for: {list(radar_settings_dict.keys())}")

# Load dataset settings and create Dataset object
data = load_dataset_settings("config/dataset_settings.json", radar_settings_dict)
print(f"✅ Dataset settings loaded with time range: {data.time_range}")
print(f"✅ Standard dimension names: {data.standard_dimension_names}")


# ------------------------------------------------------
# Loading the datasets and pre-processing them
# ------------------------------------------------------
print("\n\n--------- 2) Loading the datasets and pre-processing them ---------")
# Generate list of days in the specified time range for folder navigation and file loading
# days, days_in_time_range = get_days_in_time_range(start_time, end_time)
# print(f"🕚 Days in time range: {days_in_time_range[0:3]} to {days_in_time_range[-3:]}")  # Print first 3 and last 3 days
# from pre_processing import load_and_preprocess_datasets
# radar_datasets = load_and_preprocess_datasets(radars_to_process, days_in_time_range, dataset_dims)
# print("\n✅ Datasets loaded and pre-processed for all radars.")


# # ------------------------------------------------------
# # Calculating occurrences and sensitivity before cleanup 
# # ------------------------------------------------------
# print("\n\n--------- 3) Calculating occurrences and sensitivity before cleanup ---------")
# from cleanup_and_alignment import calculate_occurrences, calculate_sensitivity, create_global_bin_edges

# threshold = 0.999
# min_samples_per_height = 50
# bin_edges = create_global_bin_edges(radar_datasets, bin_size=0.1)

# for radar_handle, ds in radar_datasets.items():
#     print(f"Calculating occurrences and sensitivity for radar: {radar_handle}")
#     radar_datasets[radar_handle] = calculate_occurrences(ds, bin_edges=bin_edges, use_aligned=False)
#     radar_datasets[radar_handle] = calculate_sensitivity(radar_datasets[radar_handle], threshold=threshold, min_samples_threshold=min_samples_per_height)

# print("\n✅ Occurrences and sensitivity calculated for all radars before cleanup.")


# # ------------------------------------------------------
# # Clean up and alignment of the datasets
# # ------------------------------------------------------
# from cleanup_and_alignment import cleanup_and_align_datasets
# print("\n\n--------- 4) Clean up and alignment of the datasets ---------")
# radar_datasets = cleanup_and_align_datasets(radar_datasets, start_time, end_time)
# print("\n✅ Datasets cleaned up and aligned.")


# # ------------------------------------------
# # CLOUD DETECTION ALGORITHM
# # ------------------------------------------
# print("\n\n--------- 5) Running cloud detection algorithm ---------")
# from cloud_detection import run_cloud_detection_algorithm
# radar_datasets = run_cloud_detection_algorithm(radar_datasets)
# print("\n✅ Cloud detection algorithm completed for all radars.")


# # ---------------------------------
# # CLOUD STATISTICS
# # ---------------------------------
# print("\n\n--------- 6) Calculating cloud statistics ---------")
# from cloud_statistics import calculate_cloud_statistics
# radar_datasets = calculate_cloud_statistics(radar_datasets)
# print("\n✅ Cloud statistics calculated for all radars.")

# # ---------------------------------
# # PLOTTING
# # ---------------------------------
# print("\n\n--------- 7) Generating plots ---------")
# from cloud_plotting import plot_radar_sensitivity_profiles, plot_time_fraction_profiles
# # Radar sensitivity profiles
# plot_radar_sensitivity_profiles(radar_datasets)

# # Time fraction profiles
# plot_time_fraction_profiles(radar_datasets)
# print("\n✅ Plots generated for all radars.")