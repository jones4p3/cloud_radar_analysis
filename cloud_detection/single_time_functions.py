import numpy as np
import sys

def get_single_time_from_input(single_time_input, ds, debug=False):
    if debug: print(f"- Getting single time from input: {single_time_input} of type {type(single_time_input)}")
    if single_time_input is False:
        is_inside = False
    else:
        time_to_test = np.datetime64(single_time_input)
        is_inside = (time_to_test >= ds["time"].values.min()) and (time_to_test <= ds["time"].values.max())
    if isinstance(single_time_input, str) or isinstance(single_time_input, np.datetime64):
        if is_inside:
            try:
                nearest_time = ds.sel(time=single_time_input, method="nearest")["time"].values
                if debug: print(f"  Selected nearest time {nearest_time} for input {single_time_input}")
                return nearest_time
            except Exception as e:
                sys.exit(f" ⚠️ ERROR: Could not find nearest time for input string {single_time_input}: {e}")
    if (single_time_input is False) or (single_time_input is True) or not is_inside:
        ds_times = ds["time"].values
        n_times = len(ds_times)
        rnd_number = np.random.randint(0,n_times)
        single_time = ds_times[rnd_number]
        if debug:
            print(f"    Given time input is inside dataset time range: {is_inside}")
            print(f"    Randomly selected single time: {single_time} with rnd_number: {rnd_number} from 0-{n_times} available time steps.")
            print(f"---- RESULT: Selected single time for analysis: {single_time} ----\n")
        return single_time
    else:
        sys.exit(f" ⚠️ ERROR: single_time_input must be either bool, str, or datetime64, got {type(single_time_input)}")

def get_single_time_reflectivity_min_max(general_settings, single_time, cloud_detection_settings, debug=False):
    ze_min = np.inf
    ze_max = -np.inf
    data = general_settings.get("data", None)
    use_threshold = general_settings.get("use_threshold", False)

    for radar_slug, ds in data.items():
        
        ds = ds.sel(time=single_time, method="nearest")
        ze = ds["ze"]

        # Apply threshold if set
        if use_threshold:
            if debug: print(f"Applying reflectivity threshold for radar: {radar_slug}")
            current_ze_min = cloud_detection_settings.get("ze_threshold_in_dbz", -30)
            current_ze_max = np.nanmax(ze.values)
        else:
            current_ze_min = np.nanmin(ze.values)
            current_ze_max = np.nanmax(ze.values)

        # Look for overall min and max
        if current_ze_min < ze_min:
            if debug: print(f"New overall Ze min found: {current_ze_min} (previous: {ze_min})")
            ze_min = current_ze_min
        if current_ze_max > ze_max:
            if debug: print(f"New overall Ze max found: {current_ze_max} (previous: {ze_max})")
            ze_max = current_ze_max

    if debug: print(f"SINGLE Overall Ze min: {ze_min}, max: {ze_max} across all radars.")
    return ze_min, ze_max

def plot_single_time_stamp(time_ax, ds, single_time, plot_settings, cloud_detection_settings,radar_name):
    single_ze = ds["ze"].sel(time=single_time, method="nearest") # Shape (height,)
    show_distinct_ze_value_points = plot_settings["show_distinct_ze_value_points"]
    marker_size = plot_settings["marker_size"]
    height_min = plot_settings["height_min"]
    height_max = plot_settings["height_max"]
    plot_sensitivity = plot_settings["plot_sensitivity"]
    sensitivity_add_in_dbz = cloud_detection_settings["sensitivity_add_in_dbz"]
    show_all_ze_values = plot_settings["show_all_ze_values"]
    # Plotting sensitivity if needed
    if plot_sensitivity:
        sensitivity = ds["sensitivity"]
        cloud_detection_sensitivity = sensitivity + sensitivity_add_in_dbz
        cloud_detection_sensitivity.plot(ax=time_ax, y="height", linestyle="-", color="red", label="Cloud Threshold")
        sensitivity.plot(ax=time_ax, y="height", linestyle="--", color="black", label="Radar Sensitivity")
    if not show_all_ze_values:
        sensitivity_mask = (ds["sensitivity"] + sensitivity_add_in_dbz)
        threshold_mask = single_ze >= (sensitivity_mask)
        single_ze = single_ze.where(threshold_mask) # Shape (time, height)

    # Actual plotting single time ze
    marker = "o" if show_distinct_ze_value_points else None
    single_ze.plot(ax=time_ax, y="height", linestyle='-', marker=marker, markersize=marker_size*0.6)


    # Formatting single time plot
    time_ax.legend(loc='upper right', fontsize=6)
    time_str = np.datetime_as_string(single_time, unit='s').split("T")[1]
    time_ax.set_title(f"{radar_name} - Reflectivity (Ze) at {time_str}")
    time_ax.set_ylim(height_min,height_max)
    time_ax.set_ylabel("Height (m)")
    time_ax.set_xlabel("Reflectivity (dBZ)")

    return time_ax