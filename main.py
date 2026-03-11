# --------- MAIN SCRIPT ---------

# Import necessary modules
import xarray as xr

xr.set_options(
    use_new_combine_kwarg_defaults=True
)  # Setting the data_vars = 'None' as default and not 'all'

print("\n--------- 1) Loading configuration files ---------")
from config import load_radar_settings, load_dataset_settings, load_parameter_settings, print_parameter_settings

# Load radar settings and create RadarSettings objects for each radar
radar_settings_dict = load_radar_settings("config/radar_settings.json")
print(f"✅ Radar settings loaded for: {list(radar_settings_dict.keys())}")

# Load dataset settings and create Dataset object
data = load_dataset_settings("config/dataset_settings.json", radar_settings_dict)
print(f"✅ Dataset settings loaded with time range: {data.time_range}")
print(f"✅ Standard dimension names: {data.standard_dimension_names}")

# load parameter settings
params = load_parameter_settings("config/parameter_settings.json")
print_parameter_settings(params)


# ------------------------------------------------------
# Loading the datasets and pre-processing them
# ------------------------------------------------------
print("\n--------- 2) Loading the datasets and pre-processing ---------")
from pre_processing import load_and_preprocess_datasets

data = load_and_preprocess_datasets(data)
print("✅ Datasets loaded and pre-processed for all radars.")


# ------------------------------------------------------
# Calculating occurrences and sensitivity before cleanup
# ------------------------------------------------------
print(
    "\n\n--------- 3) Calculating occurrences and sensitivity before cleanup ---------"
)
from cleanup_and_alignment import calculate_occurrences_and_sensitivity_for_all_radars

data = calculate_occurrences_and_sensitivity_for_all_radars(data, params)
print("\n✅ Occurrences and sensitivity calculated for all radars before cleanup.")


# ------------------------------------------------------
# Clean up and alignment of the datasets
# ------------------------------------------------------
from cleanup_and_alignment import cleanup_and_align_datasets
print("\n\n--------- 4) Clean up and alignment of the datasets ---------")
radar_datasets = cleanup_and_align_datasets(data, params)
print("\n✅ Datasets cleaned up and aligned.")


# ------------------------------------------
# CLOUD DETECTION ALGORITHM
# ------------------------------------------
print("\n\n--------- 5) Running cloud detection algorithm ---------")
from cloud_detection import run_cloud_detection_algorithm
data = run_cloud_detection_algorithm(data, params)
print("\n✅ Cloud detection algorithm completed for all radars.")


# ---------------------------------
# CLOUD STATISTICS
# ---------------------------------
print("\n\n--------- 6) Calculating cloud statistics ---------")
from cloud_statistics import calculate_cloud_statistics
data = calculate_cloud_statistics(data)
print("\n✅ Cloud statistics calculated for all radars.")

# ---------------------------------
# PLOTTING
# ---------------------------------
print("\n\n--------- 7) Generating plots ---------")
from cloud_plotting import plot_radar_sensitivity_profiles, plot_time_fraction_profiles
# Radar sensitivity profiles
plot_radar_sensitivity_profiles(radar_datasets)

# Time fraction profiles
plot_time_fraction_profiles(radar_datasets)
print("\n✅ Plots generated for all radars.")
