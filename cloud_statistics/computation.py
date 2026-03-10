import numpy as np
from . import CloudStatisticsSettings
import xarray as xr
import dask.array as da

def select_time_range_from_dataset(ds, cfg: CloudStatisticsSettings):
    """Select a specific time range from the dataset."""
    debug = cfg.debug
    start_time, end_time = cfg.time_range
    try:
        np.datetime64(start_time)
        np.datetime64(end_time)
    except Exception as e:
        raise ValueError("Invalid time format. Please use a format compatible with numpy.datetime64.") from e

    try:
        ds_sel = ds.sel(time=slice(start_time, end_time))
    except KeyError as e:
        raise KeyError(f"Time range {start_time} to {end_time} is out of bounds for the dataset.") from e

    if debug: 
        print(f"{ds.attrs['radar_name']}: Selecting time range from {ds_sel.time.values[0]} to {ds_sel.time.values[-1]}")

    return ds_sel

def filter_radars(radar_datasets: dict, cfg: CloudStatisticsSettings):
    """Filter the radar list to include only the specified radar."""
    radars_to_test = cfg.radars_to_test
    debug = cfg.debug
    if debug:
        print(f"Filtering for radar(s): {radars_to_test}")

    if isinstance(radars_to_test, list):
        filtered_datasets = {radar_to_add: radar_datasets[radar_to_add] for radar_to_add in radar_datasets if radar_to_add in radars_to_test}
    else:
        try:
            if radars_to_test not in radar_datasets.keys():
                raise ValueError
        except ValueError as e:
                raise ValueError(f"Radar '{radars_to_test}' not found in the radar list.") from e

        # Create a filtered dictionary with only the selected radar
        filtered_datasets = {radar_to_add: radar_datasets[radar_to_add] for radar_to_add in radar_datasets if radar_to_add == radars_to_test}

    if debug:
        print(f"-- Finished filtering for:  {list(filtered_datasets.keys())}")
    return filtered_datasets

def select_radar_datasets(radar_datasets: dict, cfg: CloudStatisticsSettings):
    """Select radar datasets based on the configuration settings."""
    selected_datasets = radar_datasets

    if cfg.radars_to_test is not None:
        selected_datasets = filter_radars(radar_datasets, cfg)
    
    if cfg.time_range is not None:
        for radar_name, ds in selected_datasets.items():
            selected_datasets[radar_name] = select_time_range_from_dataset(ds, cfg)
        if cfg.debug:
            print(f"-- Finished selecting time range {cfg.time_range} for all radars.")

    if cfg.debug:
        print(f"-- Finished selecting radar datasets: {list(selected_datasets.keys())}")

    return selected_datasets

def find_maximum_of_value_in_radars(selected_radars, var: str, nan_allowed: bool) -> int:
    maximum = 0
    for _, ds in selected_radars.items():
        var_data = ds[var]
        cleaned_var_data = var_data.dropna("time")
        if (var_data.time.size != cleaned_var_data.time.size) and not nan_allowed:
            raise ValueError("NaN values found in data after cleaning.")
        maximum = max(maximum, int(cleaned_var_data.max().item()))
    return maximum

def counts_and_percentage_for_var(ds, var: str):
    var_data = ds[var] # Here "n_layers"
    counts_per_var = var_data.groupby(var_data).count()
    n_measurements = var_data.time.size
    percentages_per_var = ((counts_per_var / n_measurements) * 100).round(2)  # To percentage
    print(f"Percentages for {var}: {percentages_per_var.values}")
    return counts_per_var, percentages_per_var

def calculate_bins(ds: xr.Dataset, var: str, bin_size: int, cfg: CloudStatisticsSettings):
    """Calculate bins for a given variable in the dataset."""
    debug = cfg.debug
    if var not in ds:
        raise KeyError(f"Variable '{var}' not found in dataset.")

    minimum, maximum = ds[var].min(), ds[var].max()
    if debug: print(f"{var} range: {minimum.values} to {maximum.values}")

    # Create height bins
    bin_size = bin_size
    bins = np.arange(minimum.values, maximum.values + bin_size, bin_size)  # 30 m bins

    if debug:
        print(f"Reducing {var} size to {bin_size} bins.")
        print(f"Original size: {ds[var].sizes[var]}")
        print(f"Bins: {bins.size}")
        print(f"{(1 - (bins.size / ds[var].sizes[var])) * 100:.2f}% reduction in size.")
    return bins

def occurrences_per_gate(ds: xr.Dataset, cloud_param: str, layer_filter=None, bins=None):
    """Calculate occurrences per gate for a given cloud parameter.
    
    Returns:
        unique_gates: Array of unique gate indices.
        occurence_fraction: Array of occurrence fractions per gate.
        heights: Corresponding heights for the gates.
        max_occurence: Maximum occurrence fraction.
        max_idx: Index of the maximum occurrence fraction.
        mean_height: Mean height of the cloud parameter.
    """
    ds = ds.chunk({'time': 'auto'})
    # Grab cloud base gates
    if layer_filter is not None:
        print(f"Using cloud layer [{layer_filter}] gates for histogram...")
        layer_mask = ds["n_layers"] == layer_filter
        cloud_param_data = ds[cloud_param].sel(layer=layer_filter).where(layer_mask)  # Use the specified layer for analysis
    else:
        cloud_param_data = ds[cloud_param]
    cloud_param_data = cloud_param_data.data.ravel() # Grab all cloud_gates with height and time, flattened to 1D
    clean_cloud_data = cloud_param_data[da.isfinite(cloud_param_data)] # Remove NaNs
    clean_cloud_data = clean_cloud_data.compute_chunk_sizes() # Rechunk after filtering

    if bins is None:
        print("Using cloud gates for counting...")
        # Get unique gates and their counts
        unique_gates, counts = da.unique(clean_cloud_data, return_counts=True)
        unique_gates, counts = da.compute(unique_gates, counts)
        unique_gates = unique_gates.astype(int)
        counts = counts.astype(np.int64)
        heights = ds['height'].isel(height=unique_gates)
        mean_height = np.mean(heights.values)
    else:
        print("Using provided bins for counting...")
        counts, bin_edges = da.histogram(clean_cloud_data, bins=bins)
        counts = counts.compute()
        unique_gates = None
        bin_centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])
        heights = bin_centers
        mean_height = np.mean(heights)

    # Compute occurrence fraction and other stuff
    if layer_filter is not None:
        print(f"Calculating occurrences for layer [{layer_filter}]...")
        n_times = int(layer_mask.sum().compute().item()) # Number of time steps with the specified layer
        total_clouds = counts.sum()
        occurrence_fraction = (counts / n_times)
        distribution_fraction = counts / total_clouds if total_clouds > 0 else counts
    else:
        n_times = ds['time'].size
        total_clouds = counts.sum()
        occurrence_fraction = (counts / n_times)
        distribution_fraction = counts / total_clouds if total_clouds > 0 else counts

    print(f"Original times: {n_times}")
    print(f"Clouds found: {total_clouds}")
    print(f"Sum of occurrences: {np.sum(occurrence_fraction)}")
    print(f"Summed distribution: {np.sum(distribution_fraction)}")

    # Find max occurrence and index
    max_counts = np.max(counts)
    max_counts_idx = np.argmax(counts)
    print(f"Max counts: {max_counts} at index {max_counts_idx}")
    next_max = np.argmax(counts[1:])
    print(f"Next max gate index: {next_max}")

    # Statistics output
    print(f"Gate with max occurrences: {unique_gates[max_counts_idx]} (Counts: {max_counts}, Occurrence Fraction: {(occurrence_fraction[max_counts_idx]*100):.2f}%)")
    print(f"Next Gate [{unique_gates[max_counts_idx+1]}] would have counts: {counts[max_counts_idx+1] if max_counts_idx+1 < len(counts) else 'N/A'}, Occurence Fraction: {(occurrence_fraction[max_counts_idx+1]*100) if max_counts_idx+1 < len(occurrence_fraction) else 'N/A'}%")
    return occurrence_fraction, distribution_fraction, heights, mean_height