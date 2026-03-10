import numpy as np
def get_reflectivity_min_max(general_settings, time_settings, cloud_detection_settings, debug=False):

    if debug: print("- Calculating reflectivity min and max across all radars.")
    ze_min = np.inf
    ze_max = -np.inf
    data = general_settings.get("data", None)
    use_test_time_range = general_settings.get("use_test_time_range", False)
    use_threshold = general_settings.get("use_threshold", False)
    test_time_range = time_settings.get("test_time_range", None)
    ze_threshold_in_dbz = cloud_detection_settings.get("ze_threshold_in_dbz", -30)
    sensitivity_add_in_dbz = general_settings.get("sensitivity_add_in_dbz", 3)

    for radar_slug, ds in data.items():
        # Select dataset based on time range setting
        if use_test_time_range:
            if debug: print(f"  - Selecting test time range for radar: {radar_slug} - {test_time_range}")
            ds = ds.sel(time=slice(*test_time_range))
        else:
            if debug: print(f"  - Using full time range for radar: {radar_slug}")
            ds = ds

        # Applying the threshold if needed and selecting variables from dataset
        if use_threshold:
            threshold_mask = ds["ze"] >= ze_threshold_in_dbz
            ze = ds["ze"].where(threshold_mask) # Shape (time, height)
            if debug: print(f"      - Applying reflectivity threshold for radar: {radar_slug} at {ze_threshold_in_dbz} dBZ")
        else:
            if debug: print(f"      - Applying sensitivity-based threshold for radar: {radar_slug} at sensitivity + {sensitivity_add_in_dbz} dBZ")
            sensitivity_mask = (ds["sensitivity"] + sensitivity_add_in_dbz)
            threshold_mask = ds["ze"] >= (sensitivity_mask)
            ze = ds["ze"].where(threshold_mask) # Shape (time, height)

        # Get min and max of whole dataset for current radar
        current_ze_min = np.nanmin(ze.values)
        current_ze_max = np.nanmax(ze.values)
        
        # Look for overall min and max
        if current_ze_min < ze_min:
            if debug: print(f"      - New overall Ze min found: {current_ze_min} (previous: {ze_min})")
            ze_min = current_ze_min
        if current_ze_max > ze_max:
            if debug: print(f"      - New overall Ze max found: {current_ze_max} (previous: {ze_max})")
            ze_max = current_ze_max
    
    if debug: print(f"---- RESULT: Overall Ze min: {ze_min:.2f}, max: {ze_max:.2f} across all radars. Used for color scale limits.\n")
    return ze_min, ze_max

def get_height_min_max_with_valid_ze(general_settings, time_settings, debug=False):
    height_min = np.inf
    height_max = -np.inf
    data = general_settings.get("data", None)
    use_test_time_range = general_settings.get("use_test_time_range", False)
    test_time_range = time_settings.get("test_time_range", None)

    if debug: print("- Calculating height min and max with valid Ze across all radars.")
    for radar_slug, ds in data.items():
        # Select dataset based on time range setting
        if use_test_time_range:
            if debug: print(f"  - Selecting test time range for radar: {radar_slug} - {test_time_range}")
            ds = ds.sel(time=slice(*test_time_range))
        else:
            if debug: print(f"  - Using full time range for radar: {radar_slug}")
            ds = ds

        ze = ds["ze"]
        height = ds["height"].compute()

        valid_ze_ranges = ze.notnull().any(dim="time")
        current_height_min = height.where(valid_ze_ranges).min().values
        current_height_max = height.where(valid_ze_ranges).max().values

        if current_height_min < height_min:
            if debug: print(f"      - New overall height min found: {current_height_min} (previous: {height_min})")
            height_min = current_height_min
        if current_height_max > height_max:
            if debug: print(f"      - New overall height max found: {current_height_max} (previous: {height_max})")
            height_max = current_height_max
    if debug: print(f"---- RESULT: Overall height min: {height_min:.2f} m, max: {height_max:.2f} m across all radars. Used for plot limits.\n")
    return height_min, height_max